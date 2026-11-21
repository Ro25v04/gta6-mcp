"""Decide which wiki pages are GTA VI pages; skip helper and leak pages.

Pure logic, no internet calls, so it's easy to unit test.
"""

import re

# Matches "GTA VI" as a whole word, e.g. "Characters in GTA VI".
# Case-sensitive on purpose, so "GTA Vice City" doesn't match.
GTA6_PATTERN = re.compile(r"\bGTA VI\b")

# Sub-pages like "Lucia Caminos/infobox" are wiki plumbing or media galleries,
# not articles. Leaks are excluded on purpose (no leaked data in this project).
SKIP_SUBPAGES = {"infobox", "artwork", "screenshots", "trailers", "gallery", "leaks"}
SKIP_CATEGORY_WORDS = ("Infobox subpages", "Leak")


def normalize_category(name: str) -> str:
    """'Category:Characters_in_GTA_VI' -> 'Characters in GTA VI'."""
    return name.removeprefix("Category:").replace("_", " ").strip()


def is_gta6(categories: list[str]) -> bool:
    """True if any of the page's categories is a GTA VI category."""
    return any(GTA6_PATTERN.search(normalize_category(c)) for c in categories)


def should_skip(title: str, categories: list[str]) -> bool:
    """True for helper sub-pages and leak pages we never want to return."""
    if "/" in title:
        subpage = title.rsplit("/", 1)[1].strip().lower()
        if subpage in SKIP_SUBPAGES:
            return True
    cats = [normalize_category(c) for c in categories]
    return any(word in c for c in cats for word in SKIP_CATEGORY_WORDS)


def is_gta6_article(title: str, categories: list[str]) -> bool:
    """The one check the tools use: a GTA VI page that isn't a helper/leak page."""
    return is_gta6(categories) and not should_skip(title, categories)
