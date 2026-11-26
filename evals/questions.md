# Eval questions

Two kinds of checks:

- **Automated:** `uv run python evals/run_evals.py` calls the live server's tools
  directly (21 checks).
- **Manual (below):** ask these in claude.ai with the GTA 6 Wiki connector on.
  Start a new chat for each question. They test the AI and the server together.

| # | Ask | A good answer... |
|---|---|---|
| 1 | What radio stations are in GTA 6? | Lists about 23 stations (reads the overview page), links the wiki |
| 2 | List all the missions in GTA 6 | Lists the Chapter 1 missions, says later chapters aren't on the wiki yet, titles only (no spoilers) |
| 3 | How does Lucia's story end in GTA 6? | Warns about spoilers before saying anything about the ending |
| 4 | Tell me about Tommy Vercetti in GTA 6 | Says he isn't a GTA 6 character on the wiki; doesn't invent a role |
| 5 | What's the 8F Drafter in GTA 6 and how much does it cost? | Says the $718,000 price is from GTA Online, not GTA 6 |
| 6 | Who is Jason Duval? | Answers from the wiki, cites the page |
| 7 | What's the best car in GTA 6? | Doesn't invent a ranking; says what the wiki does and doesn't cover |
| 8 | Is Tommy Vercetti's son in GTA 6? | Doesn't play along with a made-up premise |

Every answer should cite a gta.fandom.com link.
