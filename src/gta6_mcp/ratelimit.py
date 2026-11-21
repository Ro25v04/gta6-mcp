"""Per-visitor rate limit: stops one person or bot from flooding the server."""

import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse

MAX_REQUESTS = 30   # per visitor...
PER_SECONDS = 60    # ...per minute


class RateLimit:
    """Wraps the web app and turns away visitors who send too many requests."""

    def __init__(self, app):
        self.app = app
        self.hits = defaultdict(deque)  # visitor IP -> times of their recent requests

    def _visitor_ip(self, scope) -> str:
        # On Railway, a proxy sits in front of us and passes the real IP in this header.
        headers = dict(scope.get("headers") or [])
        forwarded = headers.get(b"x-forwarded-for", b"").decode()
        if forwarded:
            return forwarded.split(",")[-1].strip()  # last entry = added by Railway's proxy
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # startup/shutdown events pass straight through
            return await self.app(scope, receive, send)

        now = time.monotonic()
        ip = self._visitor_ip(scope)
        hits = self.hits[ip]
        while hits and now - hits[0] > PER_SECONDS:  # forget requests older than a minute
            hits.popleft()

        if len(hits) >= MAX_REQUESTS:
            response = JSONResponse(
                {"error": "Too many requests. Please wait a minute and try again."},
                status_code=429,
                headers={"Retry-After": str(PER_SECONDS)},
            )
            return await response(scope, receive, send)

        hits.append(now)
        if len(self.hits) > 10_000:  # tidy up visitors with no recent requests
            for old_ip in [k for k, v in self.hits.items() if not v]:
                del self.hits[old_ip]
        await self.app(scope, receive, send)
