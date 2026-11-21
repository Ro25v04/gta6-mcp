"""Thin client for the GTA Wiki (Fandom) MediaWiki API: search, page, category.

Only fetches data. No filtering or cleaning happens here (see filters.py, clean.py).
"""

import httpx

API_URL = "https://gta.fandom.com/api.php"
HEADERS = {"User-Agent": "gta6-mcp/0.1 (+https://github.com/Ro25v04/gta6-mcp)"}
TIMEOUT = 10.0  # seconds; fail fast instead of hanging the AI app


class WikiError(Exception):
    """The wiki couldn't be reached or sent back an error."""


async def _call(params: dict) -> dict:
    """Send one request to the wiki API and return the JSON reply."""
    params = {**params, "format": "json", "formatversion": "2"}
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT) as client:
            response = await client.get(API_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        raise WikiError(f"Couldn't reach the GTA Wiki: {e}") from e
    if "error" in data and data["error"].get("code") != "missingtitle":
        raise WikiError(data["error"].get("info", "Unknown wiki error"))
    return data


async def search(query: str, limit: int = 10) -> list[dict]:
    """Search article pages. Each result includes its categories and URL,
    so filters.py can check for GTA VI without extra calls."""
    data = await _call({
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 0,  # articles only
        "gsrlimit": limit,
        "prop": "categories|info",
        "cllimit": "max",
        "inprop": "url",
    })
    pages = data.get("query", {}).get("pages", [])
    return sorted(pages, key=lambda p: p.get("index", 0))  # keep search ranking


async def get_page(title: str) -> dict | None:
    """Get one page's raw wiki markup, section list and categories.
    Returns None if the page doesn't exist."""
    data = await _call({
        "action": "parse",
        "page": title,
        "prop": "wikitext|sections|categories",
        "redirects": 1,  # follow e.g. "Lucia" -> "Lucia Caminos"
    })
    if "error" in data:  # missingtitle
        return None
    return data["parse"]


async def category_members(category: str, limit: int = 50) -> list[dict]:
    """List article pages inside a category (exact name, without 'Category:')."""
    data = await _call({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmnamespace": 0,
        "cmlimit": limit,
    })
    return data.get("query", {}).get("categorymembers", [])


async def search_categories(query: str, limit: int = 10) -> list[str]:
    """Find category names matching loose input, e.g. 'radio stations'
    -> 'Radio Stations in GTA VI'."""
    data = await _call({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 14,  # 14 = category pages
        "srlimit": limit,
    })
    results = data.get("query", {}).get("search", [])
    return [r["title"].removeprefix("Category:") for r in results]
