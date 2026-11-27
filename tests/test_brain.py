"""The rabbit's mind (brain.py): what is an occasion, what the model is told,
and that every odd answer is silence. Clara, 2026-11-27."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import hastub  # noqa: F401  (before custom_components)

from custom_components.terrier import brain

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "terrier"


def st(state: str, name: str = "Volet chambre") -> SimpleNamespace:
    return SimpleNamespace(
        state=state, entity_id="cover.x", attributes={"friendly_name": name}
    )


def test_a_change_of_state_is_an_occasion_a_reading_is_not():
    assert brain.is_occasion(st("open"), st("closed"))
    assert not brain.is_occasion(st("open"), st("open"))
    assert not brain.is_occasion(st("unavailable"), st("closed"))
    assert not brain.is_occasion(st("120.5"), st("98.2"))
    assert not brain.is_occasion(None, st("closed"))


def test_the_model_gets_the_causes_and_may_stay_silent():
    text = brain.instructions(
        "Nabazprout",
        "discreet",
        "- Porte: closed -> open",
        ["- Volet chambre: closed"],
        datetime(2026, 11, 27, 15, 0),
        "fr",
    )
    assert "Volet chambre: closed" in text and "Porte" in text
    assert "leave `say` empty" in text and "fr" in text


def test_an_odd_answer_is_silence():
    assert brain.decision(None) == ("", None)
    assert brain.decision({"say": 42}) == ("", None)
    assert brain.decision({"say": "  Bonjour   toi "}) == ("Bonjour toi", None)
    assert brain.decision({"say": "x" * 500})[0] == "x" * brain.MAX_SAY
    assert brain.decision({"left_ear": 3, "right_ear": 8}) == ("", (3, 8))
    assert brain.decision({"left_ear": 3, "right_ear": 14}) == ("", None)  # past flat
    assert brain.decision({"left_ear": 3}) == ("", None)


def test_the_daily_budget_is_shared_and_resets():
    b = brain.Budget(2)
    day = date(2026, 11, 27)
    assert b.take(day) and b.take(day) and not b.take(day)
    assert b.take(date(2026, 11, 28))


def test_every_character_is_translated():
    for path in (ROOT / "strings.json", *(ROOT / "translations").glob("*.json")):
        states = json.loads(path.read_text())["entity"]["select"]["mind"]["state"]
        assert set(states) == set(brain.CHARACTERS), path


def presence(state: str, cls: str = "occupancy") -> SimpleNamespace:
    return SimpleNamespace(
        state=state, entity_id="binary_sensor.x", attributes={"device_class": cls}
    )


def test_it_speaks_only_to_someone_in_the_room():
    """Clara, 2026-11-27: the living room's camera, the office's sensor."""
    assert brain.someone_there([presence("off"), presence("on", "motion")]) is True
    assert brain.someone_there([presence("off", "presence")]) is False
    assert (
        brain.someone_there([presence("on", "door")]) is None
    )  # not a presence sensor
    assert brain.someone_there([]) is None
