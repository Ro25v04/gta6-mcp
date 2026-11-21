"""Do the three tools respond correctly? The wiki is faked with saved pages."""

import asyncio

import pytest

from gta6_mcp import server, wiki
from tests.conftest import load_page

SAVED = {
    "Gear Up": "gear_up",
    "Lucia Caminos": "lucia_caminos",
    "8F Drafter": "8f_drafter",
    "Missions in Grand Theft Auto VI": "missions",
}


@pytest.fixture(autouse=True)
def fake_wiki(monkeypatch):
    """Replace every internet call in wiki.py with saved data."""

    async def get_page(title):
        return load_page(SAVED[title]) if title in SAVED else None

    async def page_exists(title):
        return title in SAVED

    async def category_members(category, limit=50):
        if category == "Missions in GTA VI":
            return [{"title": "Gear Up"}, {"title": "Gone Fishing (Grand Theft Auto VI)"}][:limit]
        return []

    async def search_categories(query, limit=10):
        return []

    async def search(query, limit=10):
        if query == "Lucia":
            return [
                {"title": "Lucia Caminos", "fullurl": "u1", "categories": [{"title": "Category:Characters in GTA VI"}]},
                {"title": "Lucia Armendariz", "fullurl": "u2", "categories": [{"title": "Category:Real-world voice actors"}]},
                {"title": "Lucia Caminos/infobox", "fullurl": "u3", "categories": [{"title": "Category:Infobox subpages"}]},
            ]
        return []

    for name, fake in [("get_page", get_page), ("page_exists", page_exists),
                       ("category_members", category_members),
                       ("search_categories", search_categories), ("search", search)]:
        monkeypatch.setattr(wiki, name, fake)


def run(coro):
    return asyncio.run(coro)


def test_every_response_has_source_and_licence():
    for response in [run(server.get_article("Gear Up")), run(server.search_gta6("Lucia")),
                     run(server.list_category("missions"))]:
        assert response["source"] == "GTA Wiki (Fandom)"
        assert "CC BY-SA" in response["licence"]


def test_search_keeps_only_gta6_articles():
    results = run(server.search_gta6("Lucia"))["results"]
    assert [r["title"] for r in results] == ["Lucia Caminos"]


def test_search_with_no_results_is_honest():
    response = run(server.search_gta6("flying unicorn"))
    assert response["results"] == []
    assert "Nothing about this" in response["note"]


def test_missing_page_says_not_on_wiki():
    assert "No page with this title" in run(server.get_article("Not A Real Page"))["note"]


def test_article_has_url_and_content():
    response = run(server.get_article("Gear Up"))
    assert response["url"] == "https://gta.fandom.com/wiki/Gear_Up"
    assert "Ammu-Nation" in response["content"]


def test_spoiler_warning_on_spoiler_pages():
    assert any("SPOILER" in n for n in run(server.get_article("Lucia Caminos"))["notes"])
    assert not any("SPOILER" in n for n in run(server.get_article("Gear Up"))["notes"])


def test_multi_game_warning_on_shared_pages():
    notes = run(server.get_article("8F Drafter"))["notes"]
    assert any("several games" in n for n in notes)


def test_unknown_section_lists_real_ones():
    response = run(server.get_article("Gear Up", "Ending"))
    assert "No section called" in response["note"]
    assert "Overview" in response["sections"]


def test_single_long_section_is_not_cut():
    response = run(server.get_article("Missions in Grand Theft Auto VI", "Chapter 1: Just Like Paradise"))
    assert "Discharge Time" in response["content"]  # the last mission


def test_list_category_finds_full_name_overview_page():
    response = run(server.list_category("missions"))
    assert response["category"] == "Missions in GTA VI"
    assert response["overview_page"] == "Missions in Grand Theft Auto VI"


def test_unknown_category_is_honest():
    assert "No GTA VI category" in run(server.list_category("unicorns"))["note"]
