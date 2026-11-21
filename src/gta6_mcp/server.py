"""MCP server entry point: defines the 3 tools and starts the HTTP server."""

import os
from urllib.parse import quote

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from gta6_mcp import clean, filters, wiki

SOURCE = "GTA Wiki (Fandom)"
LICENCE = "CC BY-SA (https://www.fandom.com/licensing)"
WIKI_URL = "https://gta.fandom.com/wiki/"

SPOILER_NOTE = (
    "SPOILER WARNING: this page contains GTA VI story spoilers. "
    "Warn the user before revealing plot details or the ending."
)
SHORT_NOTE = "This page is short; the wiki may not fully cover this yet."
CITE = "Always cite the page url in your answer."

# Everyday words people use -> the wiki's category name.
CATEGORY_ALIASES = {
    "cars": "Vehicles", "vehicle": "Vehicles", "guns": "Weapons",
    "radio": "Radio Stations", "songs": "Radio Stations", "music": "Radio Stations",
    "people": "Characters", "places": "Locations",
}

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

mcp = MCPServer(
    name="gta6-mcp",
    instructions=(
        "Answers questions about Grand Theft Auto VI using the GTA Wiki. "
        "Unofficial; not affiliated with Rockstar Games or Take-Two. "
        f"{CITE} Respect spoiler warnings."
    ),
)


def _url(title: str) -> str:
    return WIKI_URL + quote(title.replace(" ", "_"), safe="/:'(),")


def _with_source(response: dict) -> dict:
    """Every response carries where it came from and its licence."""
    return {**response, "source": SOURCE, "licence": LICENCE}


@mcp.tool(annotations=READ_ONLY)
async def search_gta6(query: str, limit: int = 5) -> dict:
    """Search the GTA Wiki for GTA VI pages (characters, missions, vehicles,
    places, radio stations...). Returns page titles and URLs; use get_article
    to read one. Cite the page url in your answer."""
    limit = max(1, min(limit, 10))
    results = await wiki.search(query, limit * 3)  # extra, since filtering drops some
    pages = [
        {"title": p["title"], "url": p["fullurl"]}
        for p in results
        if filters.is_gta6_article(p["title"], [c["title"] for c in p.get("categories", [])])
    ][:limit]
    response = {"query": query, "results": pages}
    if not pages:
        response["note"] = (
            "Nothing about this on the GTA Wiki for GTA VI yet. "
            "Say so honestly rather than guessing."
        )
    return _with_source(response)


@mcp.tool(annotations=READ_ONLY)
async def get_article(title: str, section: str | None = None) -> dict:
    """Read a GTA VI page from the GTA Wiki as clean text, with quick facts
    from its infobox. Long pages are cut; pass `section` (from the `sections`
    list) to read one part. Respect spoiler warnings. Cite the page url."""
    page = await wiki.get_page(title)
    if page is None:
        return _with_source({
            "title": title,
            "note": "No page with this title on the GTA Wiki yet. Try search_gta6.",
        })

    url = _url(page["title"])
    categories = [c["category"] for c in page.get("categories", [])]
    if not filters.is_gta6_article(page["title"], categories):
        return _with_source({
            "title": page["title"],
            "url": url,
            "note": "This page isn't about GTA VI, so it's not available here.",
        })

    parsed = clean.parse_page(page["wikitext"])
    section_titles = [s["title"] for s in parsed["sections"]]
    content, truncated = clean.to_text(parsed, section)
    if section and not content:
        return _with_source({
            "title": page["title"],
            "url": url,
            "sections": section_titles,
            "note": f"No section called '{section}'. Pick one from `sections`.",
        })

    notes = []
    if parsed["spoilers"]:
        notes.append(SPOILER_NOTE)
    if parsed["stub"] or parsed["word_count"] < 100:
        notes.append(SHORT_NOTE)
    if truncated:
        notes.append("Text was cut for length. Ask for a specific section to read more.")

    return _with_source({
        "title": page["title"],
        "url": url,
        "sections": section_titles,
        "content": content,
        "notes": notes,
    })


async def _find_category(name: str) -> str | None:
    """Turn loose input like 'radio stations' into 'Radio Stations in GTA VI'."""
    base = name.strip()
    for suffix in (" in GTA VI", " GTA VI", " GTA 6", " in GTA 6"):
        base = base.removesuffix(suffix)
    base = CATEGORY_ALIASES.get(base.lower(), base)

    # 1. Try the wiki's usual naming, e.g. "Missions in GTA VI".
    for guess in (base[:1].upper() + base[1:], base.title()):
        if await wiki.category_members(f"{guess} in GTA VI", 1):
            return f"{guess} in GTA VI"
    # 2. Fall back to searching category names, but only accept one that
    #    actually mentions what was asked for ("unicorns" shouldn't match "Vehicles").
    word = base.lower().rstrip("s")
    for found in await wiki.search_categories(f"{base} GTA VI"):
        if filters.is_gta6([found]) and word in found.lower():
            return found
    return None


@mcp.tool(annotations=READ_ONLY)
async def list_category(category: str, limit: int = 50) -> dict:
    """List GTA VI pages of one kind from the GTA Wiki, e.g. 'missions',
    'vehicles', 'characters', 'radio stations', 'weapons', 'locations'.
    Use get_article to read any of them. Cite the category url."""
    limit = max(1, min(limit, 200))
    name = await _find_category(category)
    if name is None:
        return _with_source({
            "category": category,
            "note": (
                "No GTA VI category like this on the wiki yet. Try: missions, "
                "vehicles, characters, radio stations, weapons, locations."
            ),
        })

    members = await wiki.category_members(name, limit)
    pages = [
        {"title": m["title"], "url": _url(m["title"])}
        for m in members
        if not filters.should_skip(m["title"], [])
    ]
    response = {"category": name, "url": _url(f"Category:{name}"), "count": len(pages), "pages": pages}
    if len(members) == limit:
        response["note"] = f"Showing the first {limit}; there may be more."
    return _with_source(response)


def main() -> None:
    """Start the server. Railway sets PORT; locally it defaults to 8000."""
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",          # listen on all interfaces so Railway can reach it
        port=port,               # served at http://<host>:<port>/mcp
        stateless_http=True,     # no per-user sessions: simpler and scales on Railway
        json_response=True,
    )


if __name__ == "__main__":
    main()
