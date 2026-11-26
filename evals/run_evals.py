"""End-to-end evals: call the LIVE server like an AI app would and check the answers.

Unlike the unit tests, this uses the real server and the real (changing) wiki, so the
checks look at properties ("has a spoiler warning"), not exact text.

    uv run python evals/run_evals.py                    # the live Railway server
    uv run python evals/run_evals.py http://localhost:8000/mcp   # a local server
"""

import json
import sys
import time

import httpx

URL = sys.argv[1] if len(sys.argv) > 1 else "https://gta6-mcp-production-d889b339.up.railway.app/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}


def call(tool: str, **args) -> dict:
    """Call one tool on the server and return its JSON response."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}
    for _ in range(3):
        r = httpx.post(URL, json=body, headers=HEADERS, timeout=60)
        if r.status_code == 429:  # hit our own rate limit: wait and retry
            time.sleep(int(r.headers.get("Retry-After", "60")))
            continue
        r.raise_for_status()
        return json.loads(r.json()["result"]["content"][0]["text"])
    raise RuntimeError("still rate limited after retries")


def notes(r: dict) -> str:
    return " ".join(r.get("notes", [])) + " " + r.get("note", "")


def titles(r: dict, key: str) -> list[str]:
    return [p["title"] for p in r.get(key, [])]


# (name, tool call, check). Each check returns True if the answer is good.
EVALS = [
    # --- search_gta6 ---
    ("Search finds the main character first",
     lambda: call("search_gta6", query="Lucia"),
     lambda r: titles(r, "results")[:1] == ["Lucia Caminos"]),
    ("Search drops other games and helper pages",
     lambda: call("search_gta6", query="Lucia"),
     lambda r: not any(t in titles(r, "results") for t in ("Lucia Armendariz", "Lucia Caminos/infobox"))),
    ("Search for Vice City returns only the GTA 6 version",
     lambda: call("search_gta6", query="Vice City"),
     lambda r: "Grand Theft Auto: Vice City" not in titles(r, "results")),
    ("Search finds the other protagonist",
     lambda: call("search_gta6", query="Jason Duval"),
     lambda r: "Jason Duval" in titles(r, "results")),
    ("Search for an older-game character is honestly empty",
     lambda: call("search_gta6", query="Tommy Vercetti"),
     lambda r: r["results"] == [] and "Nothing about this" in notes(r)),

    # --- get_article ---
    ("Article has clean text, quick facts and a URL",
     lambda: call("get_article", title="Gear Up"),
     lambda r: r["url"].endswith("/Gear_Up") and "Quick facts" in r["content"] and "[[" not in r["content"]),
    ("Spoiler pages carry a spoiler warning",
     lambda: call("get_article", title="Lucia Caminos"),
     lambda r: "SPOILER" in notes(r)),
    ("Unwritten sections never show wiki placeholders",
     lambda: call("get_article", title="Lucia Caminos"),
     lambda r: r.get("content") and "To Be Added" not in r["content"]),
    ("Redirects are followed",
     lambda: call("get_article", title="Lucia"),
     lambda r: r.get("title") == "Lucia Caminos"),
    ("Non-GTA-6 pages are refused",
     lambda: call("get_article", title="Tommy Vercetti"),
     lambda r: "isn't about GTA VI" in notes(r) and "content" not in r),
    ("Missing pages say so honestly",
     lambda: call("get_article", title="Definitely Not A Real Page 123"),
     lambda r: "No page with this title" in notes(r)),
    ("Unknown sections list the real ones",
     lambda: call("get_article", title="Gear Up", section="Ending"),
     lambda r: "No section called" in notes(r) and r.get("sections")),
    ("Shared pages warn the facts may be from another game",
     lambda: call("get_article", title="8F Drafter"),
     lambda r: "several games" in notes(r)),
    ("Long mission table comes through whole when read as one section",
     lambda: call("get_article", title="Missions in Grand Theft Auto VI", section="Chapter 1: Just Like Paradise"),
     lambda r: "Gone Fishing" in r["content"] and "Discharge Time" in r["content"]),
    ("Cut pages say exactly what's missing",
     lambda: call("get_article", title="Missions in Grand Theft Auto VI"),
     lambda r: "cut for length" not in notes(r) or "Call get_article with section=" in notes(r)),
    ("No leak sections or junk table lines",
     lambda: call("get_article", title="Radio Stations in GTA VI"),
     lambda r: not any("leak" in s.lower() for s in r["sections"])
     and not any(line.strip() and set(line.strip()) <= set("| ") for line in r["content"].splitlines())),

    # --- list_category ---
    ("Radio stations point to the full overview page",
     lambda: call("list_category", category="radio stations"),
     lambda r: r.get("overview_page") == "Radio Stations in GTA VI" and r["count"] >= 10),
    ("Missions find the overview page under its full name",
     lambda: call("list_category", category="missions"),
     lambda r: r.get("overview_page") == "Missions in Grand Theft Auto VI"),
    ("Everyday words work ('cars' -> vehicles)",
     lambda: call("list_category", category="cars"),
     lambda r: r.get("category") == "Vehicles in GTA VI" and r["count"] > 0),
    ("Characters list includes a protagonist",
     lambda: call("list_category", category="characters", limit=200),
     lambda r: "Lucia Caminos" in titles(r, "pages")),
    ("Made-up categories are honest",
     lambda: call("list_category", category="unicorns"),
     lambda r: "No GTA VI category" in notes(r)),
]


def main() -> None:
    print(f"Running {len(EVALS)} evals against {URL}\n")
    passed = 0
    for name, run, check in EVALS:
        try:
            r = run()
            ok = bool(check(r)) and r.get("source") == "GTA Wiki (Fandom)" and "CC BY-SA" in r.get("licence", "")
        except Exception as e:  # a crash counts as a failure, with the reason shown
            ok, name = False, f"{name}  ({type(e).__name__}: {e})"
        passed += ok
        print(f"{'✅' if ok else '❌'} {name}")
    print(f"\n{passed}/{len(EVALS)} passed")
    sys.exit(0 if passed == len(EVALS) else 1)


if __name__ == "__main__":
    main()
