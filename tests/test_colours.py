"""The belly is not an RGB bulb, and the integration must not pretend it is."""

from __future__ import annotations

import ast
from pathlib import Path

import hastub  # noqa: F401  (before custom_components)
import yaml

from custom_components.terrier import const
from custom_components.terrier.light import nearest_colour, nearest_level

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "terrier"

# The warren's palette (terrier indicators.BELLY_PALETTE), copied by hand:
# the integration cannot import the Terrier, whose code is private. Review of
# 2026-11-18: three tables in this repository disagreed with it and with
# each other. contract/ checks this list against a running warren.
WARREN_PALETTE = {"blue", "green", "cyan", "red", "violet", "yellow", "white"}
WARREN_OLD_NAMES = {
    "warm": "red",
    "amber": "red",
    "rose": "red",
    "orange": "red",
    "sky": "cyan",
}


def test_the_palette_is_the_warrens():
    assert set(const.COLOURS) == WARREN_PALETTE
    assert set(const.BELLY_COLOURS) == WARREN_PALETTE
    assert const.DEFAULT_COLOUR in WARREN_PALETTE


def test_older_names_read_as_the_warren_reads_them():
    for old, new in WARREN_OLD_NAMES.items():
        assert const.canon(old) == new
    for name in WARREN_PALETTE:
        assert const.canon(name) == name
    assert const.canon("teal") is None
    assert const.canon(None) is None


def test_the_select_offers_the_palette():
    tree = ast.parse((COMPONENT / "settings.py").read_text("utf-8"))
    options = next(
        ast.literal_eval(kw.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and any(
            k.arg == "key" and getattr(k.value, "value", None) == "nightlight_colour"
            for k in node.keywords
        )
        for kw in node.keywords
        if kw.arg == "options"
    )
    assert tuple(options) == const.BELLY_COLOURS


def test_the_actions_offer_what_the_code_accepts():
    """services.yaml is what the UI shows; const is what the schema checks."""
    spec = yaml.safe_load((COMPONENT / "services.yaml").read_text())

    def options(service, field):
        return spec[service]["fields"][field]["selector"]["select"]["options"]

    assert options("notify", "colour") == list(const.BELLY_COLOURS)
    assert options("ambient", "colour") == list(const.BELLY_COLOURS)
    assert options("tell", "what") == list(const.TELL)
    assert options("rfid_bind", "type") == list(const.ACTION_TYPES)
    assert options("button_bind", "type") == list(const.ACTION_TYPES)


def test_each_real_colour_maps_to_itself():
    """The round trip has to hold, or the light reports a state it is not in."""
    for name, rgb in const.COLOURS.items():
        assert nearest_colour(rgb) == name, name


def test_an_impossible_colour_lands_somewhere_sensible():
    assert nearest_colour((0, 0, 0)) in const.COLOURS
    assert nearest_colour((255, 255, 255)) == "white"
    assert nearest_colour((0, 0, 255)) == "blue"
    assert nearest_colour((0, 255, 0)) == "green"
    assert nearest_colour((255, 0, 0)) == "red"
    assert nearest_colour((255, 255, 0)) == "yellow"
    assert nearest_colour((0, 255, 255)) == "cyan"


def test_brightness_maps_onto_the_five_levels_the_hardware_has():
    assert nearest_level(255) == 5
    assert nearest_level(0) == 1
    assert nearest_level(64) == 2
    for level, value in {1: 31, 2: 64, 3: 115, 4: 179, 5: 255}.items():
        assert nearest_level(value) == level


def test_brightness_is_monotonic():
    """Asking for more light must never give less."""
    levels = [nearest_level(b) for b in range(0, 256, 5)]
    assert levels == sorted(levels)
