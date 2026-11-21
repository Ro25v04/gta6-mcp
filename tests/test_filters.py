"""Is this a GTA VI page we should return?"""

from gta6_mcp.filters import is_gta6, is_gta6_article, normalize_category, should_skip


def test_normalize_handles_both_wiki_formats():
    assert normalize_category("Category:Characters in GTA VI") == "Characters in GTA VI"
    assert normalize_category("Characters_in_GTA_VI") == "Characters in GTA VI"


def test_gta6_character_is_kept():
    assert is_gta6_article("Lucia Caminos", ["Category:Characters in GTA VI", "Category:Protagonists"])


def test_other_game_page_is_dropped():
    # Lucia Armendariz: a real voice actor from an older game
    assert not is_gta6_article("Lucia Armendariz", ["Category:Real-world voice actors"])


def test_vice_city_stories_does_not_count_as_gta6():
    assert not is_gta6(["Characters in GTA Vice City Stories"])


def test_infobox_subpage_is_dropped():
    assert should_skip("Lucia Caminos/infobox", ["Category:Infobox subpages"])
    assert not is_gta6_article("Lucia Caminos/infobox", ["Characters in GTA VI", "Infobox subpages"])


def test_leak_pages_are_dropped():
    assert not is_gta6_article("Grand Theft Auto VI/Leaks", ["Category:GTA VI"])
    assert not is_gta6_article("Some Page", ["Category:GTA VI", "Category:Leaked content"])


def test_real_article_with_slash_in_title_is_kept():
    title = "Unnamed GTA VI Heckler & Koch MP5/40-inspired submachine gun"
    assert is_gta6_article(title, ["Weapons in GTA VI"])
