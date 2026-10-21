"""The belly is not an RGB bulb, and the integration must not pretend it is."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "terrier"


def _load(name: str):
    """Import one module without importing Home Assistant.

    light.py imports homeassistant at module level, so the two functions under
    test are read out of the source and executed on their own. Worth the
    awkwardness: snapping a colour wrongly is silent, and it is the one piece
    of real logic in this integration.
    """
    import ast

    src = (COMPONENT / name).read_text()
    tree = ast.parse(src)
    keep = [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef)
        and n.name in ("nearest_colour", "nearest_level")
    ]
    module = ast.Module(body=keep, type_ignores=[])
    ns: dict = {}
    const = importlib.util.spec_from_file_location("c", COMPONENT / "const.py")
    cm = importlib.util.module_from_spec(const)
    sys.modules["c"] = cm
    const.loader.exec_module(cm)
    ns["COLOURS"] = cm.COLOURS
    ns["LEVELS"] = {1: 31, 2: 64, 3: 115, 4: 179, 5: 255}
    import math

    ns["math"] = math
    exec(compile(module, "light.py", "exec"), ns)
    return ns


NS = _load("light.py")
nearest_colour = NS["nearest_colour"]
nearest_level = NS["nearest_level"]
COLOURS = NS["COLOURS"]


def test_each_real_colour_maps_to_itself():
    """The round trip has to hold, or the light reports a state it is not in."""
    for name, rgb in COLOURS.items():
        assert nearest_colour(rgb) == name, name


def test_an_impossible_colour_lands_somewhere_sensible():
    assert nearest_colour((0, 0, 0)) in COLOURS
    assert nearest_colour((255, 255, 255)) == "white"
    assert nearest_colour((0, 0, 255)) == "blue"
    assert nearest_colour((0, 255, 0)) == "green"
    assert nearest_colour((255, 0, 0)) in ("amber", "rose")


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
