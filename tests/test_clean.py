"""Is wiki markup turned into clean, honest text?"""

from gta6_mcp.clean import NOT_WRITTEN, parse_page, to_text


def _intro(wikitext: str) -> str:
    return parse_page(wikitext)["sections"][0]["text"]


# --- Markup cleaning -------------------------------------------------------

def test_game_templates_become_words():
    assert _intro("A radio station in {{VI}}.") == "A radio station in Grand Theft Auto VI."


def test_links_become_their_words():
    assert _intro("One of the [[Protagonist|protagonists]], with [[Jason Duval]].") == (
        "One of the protagonists, with Jason Duval."
    )


def test_references_images_and_bold_are_removed():
    text = _intro("'''Gear Up''' is a mission.<ref>Some source</ref>[[File:Car.png|thumb]]")
    assert text == "Gear Up is a mission."


def test_quote_template_keeps_its_text():
    assert _intro("{{Quote|Who you know and what you got.|Lucia}}") == '"Who you know and what you got."'


def test_empty_table_rows_are_removed():
    wikitext = 'Intro text.\n{| class="wikitable"\n|-\n|\n|\n|}\nMore text.'
    assert "|" not in _intro(wikitext)


# --- Sections ----------------------------------------------------------------

def test_useless_and_leak_sections_are_dropped():
    wikitext = "Intro.\n==History==\nReal.\n==Development Leaks==\nLeaked.\n==Gallery==\nPics.\n==References==\nRefs."
    titles = [s["title"] for s in parse_page(wikitext)["sections"]]
    assert titles == ["Introduction", "History"]


def test_placeholder_section_says_not_on_wiki_yet(page):
    lucia = parse_page(page("lucia_caminos")["wikitext"])
    ending = next(s for s in lucia["sections"] if s["title"] == "Ending")
    assert ending["text"] == NOT_WRITTEN


def test_spoiler_flag_is_set(page):
    assert parse_page(page("lucia_caminos")["wikitext"])["spoilers"]
    assert not parse_page(page("gear_up")["wikitext"])["spoilers"]


# --- Quick facts (infobox) ---------------------------------------------------

def test_quick_facts_come_from_infobox(page):
    facts = parse_page(page("gear_up")["wikitext"])["facts"]
    assert facts["For"] == "Andrew"
    assert facts["Unlocks"] == "Lab Fees"


def test_quick_facts_skip_image_fields(page):
    facts = parse_page(page("8f_drafter")["wikitext"])["facts"]
    assert facts["Manufacturer"] == "Obey"
    assert not any(".png" in v or ".jpg" in v for v in facts.values())


# --- Length limit (bugs found in live testing) -------------------------------

def test_long_table_keeps_its_rows_when_cut(page):
    missions = parse_page(page("missions")["wikitext"])
    text, cut = to_text(missions, "Chapter 1: Just Like Paradise")
    assert cut is not None  # this section is over the default limit
    assert "Gone Fishing" in text and "Building a Life" in text  # rows kept, not dropped


def test_cut_report_names_the_right_sections(page):
    missions = parse_page(page("missions")["wikitext"])
    _, cut = to_text(missions)
    assert cut == {"cut_in": "Chapter 1: Just Like Paradise", "not_included": ["Side Missions"]}


def test_short_page_is_not_cut(page):
    _, cut = to_text(parse_page(page("gear_up")["wikitext"]))
    assert cut is None


def test_single_section_has_only_that_section(page):
    text, _ = to_text(parse_page(page("afrobank_fm")["wikitext"]), "Description")
    assert text.startswith("## Description")
    assert "Quick facts" not in text and "## Introduction" not in text
