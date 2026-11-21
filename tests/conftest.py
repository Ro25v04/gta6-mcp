"""Shared test helpers: load saved wiki pages from tests/fixtures/."""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_page(name: str) -> dict:
    """A saved wiki.get_page() response, e.g. load_page("gear_up")."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def page():
    return load_page
