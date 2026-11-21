"""Does the rate limit let normal use through and stop floods?"""

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from gta6_mcp.ratelimit import MAX_REQUESTS, RateLimit


def _client() -> TestClient:
    app = Starlette(routes=[Route("/mcp", lambda request: PlainTextResponse("ok"), methods=["POST"])])
    return TestClient(RateLimit(app))


def _post(client, ip="1.1.1.1"):
    return client.post("/mcp", headers={"X-Forwarded-For": ip})


def test_normal_use_is_allowed():
    client = _client()
    assert all(_post(client).status_code == 200 for _ in range(MAX_REQUESTS))


def test_flood_gets_429():
    client = _client()
    for _ in range(MAX_REQUESTS):
        _post(client)
    response = _post(client)
    assert response.status_code == 429
    assert "Too many requests" in response.json()["error"]


def test_each_visitor_has_their_own_limit():
    client = _client()
    for _ in range(MAX_REQUESTS):
        _post(client, ip="1.1.1.1")
    assert _post(client, ip="1.1.1.1").status_code == 429
    assert _post(client, ip="2.2.2.2").status_code == 200


def test_real_ip_header_wins_over_faked_forwarded_header():
    client = _client()
    for i in range(MAX_REQUESTS):
        client.post("/mcp", headers={"X-Real-IP": "3.3.3.3", "X-Forwarded-For": f"10.0.0.{i}"})
    response = client.post("/mcp", headers={"X-Real-IP": "3.3.3.3", "X-Forwarded-For": "10.0.0.99"})
    assert response.status_code == 429
