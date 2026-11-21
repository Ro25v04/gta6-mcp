"""Turn raw wiki markup into readable plain text, split into sections, truncate.

Pure logic, no internet calls. Uses mwparserfromhell to understand wiki markup.
"""

import re

import mwparserfromhell as mw
from mwparserfromhell.nodes import (
    Comment, ExternalLink, Heading, HTMLEntity, Tag, Template, Text, Wikilink,
)

MAX_CHARS = 6000  # roughly 1,500 words; enough for an answer, cheap for the AI

# Sections that are only images, videos or wiki plumbing: nothing useful as text.
SKIP_SECTIONS = {
    "gallery", "images", "artwork", "screenshots", "trailer screenshots",
    "official screenshots", "videos", "references", "navigation", "see also",
}

# Short templates that stand for words, e.g. {{VI}} -> "Grand Theft Auto VI".
TEMPLATE_WORDS = {
    "vi": "Grand Theft Auto VI",
    "v": "Grand Theft Auto V",
    "o": "Grand Theft Auto Online",
    "iv": "Grand Theft Auto IV",
}
# Templates that wrap real text: keep the text, drop the wrapper.
KEEP_FIRST_PARAM = {"small", "quote", "h4"}  # {{Small|text}} -> text
KEEP_LAST_PARAM = {"wp"}                     # {{WP|Article|shown text}} -> shown text

# Infobox fields that are images or formatting, not facts.
SKIP_FACTS = {"name change", "games", "title"}
SKIP_FACT_WORDS = ("image", "caption", "label")  # e.g. "front image2", "caption2"

IMAGE_PREFIXES = ("file:", "image:", "category:", ":file:", ":image:")

# Sections editors haven't written yet, e.g. "To Be Added..."
PLACEHOLDER = re.compile(r"^(to be added|tba|tbd|coming soon)\W*$", re.IGNORECASE)
NOT_WRITTEN = "Not on the wiki yet."


def _name(template: Template) -> str:
    return str(template.name).strip().lower().replace("_", " ")


def _positional(template: Template) -> list:
    return [p.value for p in template.params if not p.showkey]


def _render(nodes) -> str:
    """Turn parsed wiki nodes into plain text, one node at a time."""
    out = []
    for node in nodes.nodes if hasattr(nodes, "nodes") else nodes:
        if isinstance(node, Text):
            out.append(str(node))
        elif isinstance(node, HTMLEntity):
            out.append(node.normalize())
        elif isinstance(node, Wikilink):
            if str(node.title).strip().lower().startswith(IMAGE_PREFIXES):
                continue  # images and category tags
            out.append(_render(node.text) if node.text else str(node.title))
        elif isinstance(node, ExternalLink):
            if node.title:
                out.append(_render(node.title))
        elif isinstance(node, Template):
            name, args = _name(node), _positional(node)
            if name in TEMPLATE_WORDS:
                out.append(TEMPLATE_WORDS[name])
            elif name == "quote" and args:
                out.append('"' + _render(args[0]).strip().strip('"') + '"')
            elif name in KEEP_FIRST_PARAM and args:
                out.append(_render(args[0]))
            elif name in KEEP_LAST_PARAM and args:
                out.append(_render(args[-1]))
            # every other template is wiki machinery: drop it
        elif isinstance(node, Tag):
            tag = str(node.tag).lower()
            if tag in ("ref", "gallery", "references"):
                continue
            if tag == "br":
                out.append("\n")
            elif tag == "li":
                out.append("\n- ")
            elif tag == "tr":
                out.append("\n" + (_render(node.contents) if node.contents else ""))
            elif tag in ("td", "th"):
                out.append(" | " + (_render(node.contents).strip() if node.contents else ""))
            elif node.contents:
                out.append(_render(node.contents))
        elif isinstance(node, (Comment, Heading)):
            continue
    return "".join(out)


def _tidy(text: str) -> str:
    """Collapse the extra spaces and blank lines left behind."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"^[| ]+$", "", text, flags=re.MULTILINE)  # empty table rows like "| | |"
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _facts(code) -> dict[str, str]:
    """Pull key facts out of the page's infobox, e.g. {'Host': 'Burna and Palmsy'}."""
    for template in code.filter_templates(recursive=False):
        if _name(template).startswith("infobox"):
            facts = {}
            for p in template.params:
                key = str(p.name).strip().replace("_", " ")
                value = _tidy(_render(p.value)).replace("\n", " ")
                lowered = key.lower()
                if (
                    not value
                    or lowered in SKIP_FACTS
                    or any(word in lowered for word in SKIP_FACT_WORDS)
                ):
                    continue
                facts[key[:1].upper() + key[1:]] = value
            return facts
    return {}


def parse_page(wikitext: str) -> dict:
    """Clean a whole page.

    Returns {"facts", "sections": [{"title", "text"}], "spoilers", "stub", "word_count"}.
    """
    code = mw.parse(wikitext)
    names = {_name(t) for t in code.filter_templates(recursive=True)}

    sections, title, current = [], "Introduction", []
    for node in code.nodes:
        if isinstance(node, Heading):
            sections.append((title, current))
            title, current = _tidy(_render(node.title)), []
        else:
            current.append(node)
    sections.append((title, current))

    kept = []
    for title, nodes in sections:
        text = _tidy(_render(nodes))
        if PLACEHOLDER.match(text):
            text = NOT_WRITTEN
        lowered = title.lower()
        if text and lowered not in SKIP_SECTIONS and "leak" not in lowered:  # no leaked info
            kept.append({"title": title, "text": text})

    return {
        "facts": _facts(code),
        "sections": kept,
        "spoilers": any(n.startswith("spoiler") for n in names),
        "stub": any(n.startswith("stub") for n in names),
        "word_count": sum(len(s["text"].split()) for s in kept),
    }


def to_text(page: dict, section: str | None = None, max_chars: int = MAX_CHARS) -> tuple[str, dict | None]:
    """Join a parsed page (or one section) into text, cut to max_chars.

    Returns (text, cut). cut is None if nothing was cut, otherwise
    {"cut_in": section title cut partway, "not_included": [later section titles]},
    so the caller can tell the AI exactly what's missing.
    Cuts at a paragraph break, or a line break if that would lose too much.
    """
    parts = []  # (section title or None for quick facts, text)
    if section is None and page["facts"]:
        parts.append((None, "Quick facts:\n" + "\n".join(f"- {k}: {v}" for k, v in page["facts"].items())))
    for s in page["sections"]:
        if section is None or s["title"].lower() == section.lower():
            parts.append((s["title"], f"## {s['title']}\n{s['text']}"))
    text = "\n\n".join(p for _, p in parts)

    if len(text) <= max_chars:
        return text, None
    cut = text.rfind("\n\n", 0, max_chars)
    if cut < max_chars // 2:  # paragraph break too early (e.g. a long table): would lose too much
        cut = text.rfind("\n", 0, max_chars)
    if cut <= 0:
        cut = max_chars

    # Work out which section the cut landed in, and which sections were left out.
    cut_in, not_included, start = None, [], 0
    for title, part in parts:
        if start < cut:
            cut_in = title if cut < start + len(part) else None  # None: this part fit fully
        elif title:
            not_included.append(title)
        start += len(part) + 2  # +2 for the "\n\n" joining parts
    return text[:cut].rstrip(), {"cut_in": cut_in, "not_included": not_included}
