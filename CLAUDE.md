Project: gta6-mcp. Unofficial MCP server that lets any MCP-compatible AI app
(Claude, ChatGPT, Cursor etc.) answer questions about GTA 6 using the GTA Wiki.

Decisions so far:
- Python, official MCP SDK v2 (MCPServer, formerly FastMCP), streamable-http transport
- Deploy on Railway (Hobby): listen on 0.0.0.0 and the PORT env var, endpoint /mcp
- Data: GTA Wiki Fandom API (https://gta.fandom.com/api.php), live calls, no database
- No agents or LLM calls inside the server; the client model is the agent
- v1 tools: search_gta6, get_article, list_category (generic, covers missions,
  radio stations, vehicles, characters etc.)
- Filter results to GTA VI pages only (wiki covers every GTA game)
- Every response includes source, page URL and licence (CC BY-SA); tool
  descriptions ask the model to cite the URL
- Text only: no images, no song lyrics, no leaked or game-file data
- Handle stubs and missing pages honestly ("not on the wiki yet")
- README: disclaimer (not affiliated with Rockstar or Take-Two), credits, MIT licence
- Tests: unit tests on the tools first, then ~20 end-to-end eval questions
- Keep v1 small and shippable; I tend to over-plan, so push me to ship

Before writing code, explain the plan in plain English and wait for my go-ahead.