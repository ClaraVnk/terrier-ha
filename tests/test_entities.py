"""The entities: which exist, and what they say. Review of 2026-11-18.

Built by each platform's own `async_setup_entry` on the stand-ins of hastub,
fed by a coordinator whose data the test sets.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import hastub  # noqa: F401  (before custom_components)

from custom_components.terrier import (
    binary_sensor,
    coordinator,
    light,
    select,
    sensor,
    switch,
)
from custom_components.terrier.const import COLOURS

A, B = "0019dbdeadbe", "0019dbfeed11"


def _rabbit(**extra):
    return {"name": "Nabi", "online": True, "config": {}, **extra}


class Entry:
    def __init__(self, data):
        client = SimpleNamespace(base_url="https://example.com")
        self.runtime_data = coordinator.TerrierCoordinator(None, None, client)
        self.runtime_data.data = data
        self.unloads = []

    def async_on_unload(self, fn):
        self.unloads.append(fn)


def _setup(platform, data):
    entry = Entry(data)
    added: list = []
    asyncio.run(platform.async_setup_entry(None, entry, added.extend))
    return entry, added


# --- M7 ---------------------------------------------------------------------
def test_a_rabbit_adopted_later_gets_its_entities():
    entry, added = _setup(binary_sensor, {A: _rabbit()})
    assert [e.unique_id for e in added] == [f"{A}_breathing"]
    entry.runtime_data.data = {A: _rabbit(), B: _rabbit()}
    entry.runtime_data.async_update_listeners()
    assert [e.unique_id for e in added] == [f"{A}_breathing", f"{B}_breathing"]
    entry.runtime_data.async_update_listeners()
    assert len(added) == 2, "nothing is added twice"


def test_the_mood_sensor_appears_when_the_mood_is_turned_on():
    entry, added = _setup(sensor, {A: _rabbit(mood={"enabled": False})})
    assert f"{A}_mood" not in {e.unique_id for e in added}
    entry.runtime_data.data = {A: _rabbit(mood={"enabled": True, "mood": 60})}
    entry.runtime_data.async_update_listeners()
    assert f"{A}_mood" in {e.unique_id for e in added}


def test_every_platform_adds_through_the_listener():
    for platform in (switch, select, light):
        entry, added = _setup(platform, {})
        assert added == []
        entry.runtime_data.data = {A: _rabbit()}
        entry.runtime_data.async_update_listeners()
        assert added, platform.__name__


# --- M1 ---------------------------------------------------------------------
def _light(colour):
    _entry, added = _setup(light, {A: _rabbit(config={"nightlight_colour": colour})})
    return added[0]


def test_the_light_shows_every_colour_the_belly_has():
    for name, rgb in COLOURS.items():
        assert _light(name).rgb_color == rgb, name


def test_the_light_shows_an_older_name_as_what_the_belly_shows():
    assert _light("warm").rgb_color == COLOURS["red"]
    assert _light("sky").rgb_color == COLOURS["cyan"]
    assert _light("orange").extra_state_attributes["colour"] == "red"


def test_the_colour_select_shows_a_stored_cyan():
    _entry, added = _setup(select, {A: _rabbit(config={"nightlight_colour": "cyan"})})
    colour = next(e for e in added if e.unique_id == f"{A}_nightlight_colour")
    assert colour.current_option == "cyan"
    assert "sky" not in colour._attr_options
    assert "orange" not in colour._attr_options


# --- L3 ---------------------------------------------------------------------
def test_the_breathing_sensor_does_not_record_the_address():
    _entry, added = _setup(binary_sensor, {A: _rabbit(last_ip="81.2.69.142")})
    assert "81.2.69.142" not in str(added[0].extra_state_attributes)


# --- L9 ---------------------------------------------------------------------
def test_the_device_carries_its_mac_as_the_registry_writes_it():
    _entry, added = _setup(binary_sensor, {A: _rabbit()})
    assert added[0].device_info["connections"] == {("mac", "00:19:db:de:ad:be")}
