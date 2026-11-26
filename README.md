# gta6-mcp

[![tests](https://github.com/Ro25v04/gta6-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/Ro25v04/gta6-mcp/actions/workflows/tests.yml)

An MCP server that gives AI assistants live access to the [GTA Wiki](https://gta.fandom.com),
so they can actually answer questions about GTA 6 and show where the answer came from.

> Unofficial fan project. Not affiliated with Rockstar Games or Take-Two Interactive.

## Why I built this

Honestly? For fun. GTA 6 was coming out, everyone was talking about it, and I wanted
an excuse to build something real with MCP. So I built a server that lets AI assistants
look things up on the GTA Wiki in real time.

I built it over a weekend and kept it small on purpose: three tools, no database, and it's deployed.

## Try it

**Claude (claude.ai)**
1. Settings → Connectors → **Add custom connector**
2. Name: `GTA 6 Wiki` · URL: `https://gta6-mcp-production-d889b339.up.railway.app/mcp`
3. Authentication: **No sign-in** → Add, then start a new chat

**Claude Code**
```
claude mcp add --transport http gta6 https://gta6-mcp-production-d889b339.up.railway.app/mcp
```

**Other MCP clients** (Cursor etc.): add a remote HTTP server with the URL above.

### Things to ask
- What radio stations are in GTA 6?
- List the missions in GTA 6
- Who is Lucia Caminos?
- What's the 8F Drafter?

## How it works

The server has three read-only tools. The AI app is the agent and decides when to call them.

| Tool | What it does |
|---|---|
| `search_gta6` | Searches the wiki for GTA 6 pages |
| `get_article` | Reads a page as clean text, or one section of it |
| `list_category` | Lists missions, vehicles, characters, radio stations and more |

A few things I cared about:

- **Live data.** Every question hits the wiki API, so answers stay current. No database.
- **GTA 6 only.** The wiki covers every GTA game, so anything that isn't GTA 6 gets filtered out.
- **Honest answers.** If the wiki hasn't covered something yet, the server says so.
  The AI shouldn't fill the gap with guesses.
- **Spoiler warnings.** Pages with story spoilers come with a note telling the AI to warn you first.
- **Text only.** No leaked content, images or song lyrics.
- **Rate limited.** Each visitor gets a fair share, and the server goes easy on the wiki.

## What testing taught me

Testing with real questions caught bugs that looked fine on paper. One example:
the missions page was getting cut for length right before the mission table, so
the AI confidently listed a fraction of the missions. Now, when the server cuts a page
for length, it tells the AI exactly which sections are missing and how to get them.

There are 36 unit tests, all running offline against saved wiki pages, and GitHub
Actions runs them before every deploy.

## Run it locally

You'll need [uv](https://docs.astral.sh/uv/).

```
uv run gta6-mcp      # serves http://localhost:8000/mcp
uv run pytest        # runs the tests
```

**Stack:** Python, MCP Python SDK, httpx, mwparserfromhell, Railway, GitHub Actions

## Heads up

Answers come from a community wiki that's still filling in after launch, so some will
be incomplete or occasionally wrong. Every answer links its source, so you can check it.

## What's next

- Telling you when something exists, but only in other GTA games
- Radio station tracklists
- Reading very long sections in parts
- Caching and uptime monitoring

Got an idea or found a bug? Open an issue.

## Credits

- Content from the [GTA Wiki](https://gta.fandom.com) and its editors, licensed [CC BY-SA](https://www.fandom.com/licensing)
- Code licensed [MIT](LICENSE)
