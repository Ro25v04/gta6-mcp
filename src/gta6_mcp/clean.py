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


def to_text(page: dict, section: str | None = None, max_chars: int = MAX_CHARS) -> tuple[str, bool]:
    """Join a parsed page (or one section) into text, cut to max_chars.

    Returns (text, was_truncated). Cuts at a paragraph break, never mid-sentence.
    """
    parts = []
    if section is None and page["facts"]:
        parts.append("Quick facts:\n" + "\n".join(f"- {k}: {v}" for k, v in page["facts"].items()))
    for s in page["sections"]:
        if section is None or s["title"].lower() == section.lower():
            parts.append(f"## {s['title']}\n{s['text']}")
    text = "\n\n".join(parts)

    if len(text) <= max_chars:
        return text, False
    cut = text.rfind("\n\n", 0, max_chars)
    return text[: cut if cut > 0 else max_chars].rstrip(), True
