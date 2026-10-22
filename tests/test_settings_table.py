"""The settings table, and the three files that have to agree with it.

`settings.py` is where a rabbit's configuration becomes Home Assistant
entities. Adding a row there means adding a name in `strings.json`, a name
in each translation and an icon in `icons.json`, and nothing in the code
will complain if you forget — the entity simply appears in somebody's
dashboard called `switch.terrier_weather_enabled`.

`test_manifest.py` already checks that every entity in `strings.json` has an
icon and that the translations match it exactly. These check the other
direction: that the table and the strings describe the same set, and that a
select's options are the states it declares. A select offering `discret`
while the strings translate `discreet` renders as the raw key, which looks
like a bug in Home Assistant rather than in us.
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPONENT = _ROOT / "custom_components" / "terrier"

PLATFORM = {"SWITCHES": "switch", "TIMES": "time",
            "SELECTS": "select", "NUMBERS": "number"}


def _tables() -> dict[str, list[dict]]:
    """Read the table without importing it — these tests run without Home
    Assistant installed, and `settings.py` imports EntityCategory."""
    tree = ast.parse((COMPONENT / "settings.py").read_text("utf-8"))
    out: dict[str, list[dict]] = {}
    for node in tree.body:
        if not (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)):
            continue
        if node.target.id not in PLATFORM or node.value is None:
            continue
        rows = []
        for call in node.value.elts:
            row = {}
            for kw in call.keywords:
                try:
                    row[kw.arg] = ast.literal_eval(kw.value)
                except ValueError:
                    row[kw.arg] = None          # EntityCategory, not a literal
            rows.append(row)
        out[node.target.id] = rows
    return out


def load(name: str) -> dict:
    return json.loads((COMPONENT / name).read_text("utf-8"))


TABLES = _tables()
ROWS = [(PLATFORM[t], row) for t, rows in TABLES.items() for row in rows]


def test_the_tables_were_found_at_all():
    """If this fails the rest are vacuously true."""
    assert set(TABLES) == set(PLATFORM)
    assert len(ROWS) > 30


def test_no_key_appears_twice():
    keys = [row["key"] for _, row in ROWS]
    assert len(keys) == len(set(keys)), "two entities would fight over one unique id"


@pytest.mark.parametrize("platform,row", ROWS, ids=[f"{p}.{r['key']}" for p, r in ROWS])
def test_every_setting_has_a_name_and_an_icon(platform, row):
    key = row["key"]
    assert key in load("strings.json")["entity"].get(platform, {}), "no English name"
    assert key in load("icons.json")["entity"].get(platform, {}), "no icon"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_setting_is_translated(lang):
    missing = []
    for platform, row in ROWS:
        entity = json.loads(
            (COMPONENT / "translations" / f"{lang}.json").read_text("utf-8")
        )["entity"]
        if row["key"] not in entity.get(platform, {}):
            missing.append(f"{platform}.{row['key']}")
    assert not missing, f"untranslated in {lang}: {missing}"


def test_a_select_offers_exactly_the_states_it_translates():
    """An option with no translation renders as its raw key, which reads as a
    bug in Home Assistant rather than in us."""
    strings = load("strings.json")["entity"]["select"]
    problems = []
    for row in TABLES["SELECTS"]:
        declared = set(row.get("options") or ())
        translated = set(strings.get(row["key"], {}).get("state") or ())
        if declared != translated:
            problems.append(
                f"{row['key']}: offers {sorted(declared - translated)} with no "
                f"translation, translates {sorted(translated - declared)} with "
                "no option"
            )
    assert not problems, "; ".join(problems)


def test_a_number_has_a_range_that_makes_sense():
    for row in TABLES["NUMBERS"]:
        assert row["minimum"] < row["maximum"], row["key"]
        assert row.get("step", 1) <= row["maximum"] - row["minimum"], row["key"]


def test_the_api_client_can_write_every_one_of_them():
    """They all go through one call, so this is really a check that the
    method is still called what the entity base calls."""
    src = (COMPONENT / "api.py").read_text("utf-8")
    assert "async def set_config" in src
    assert "async def set_config" in src and "/config" in src
    base = (COMPONENT / "config_entity.py").read_text("utf-8")
    assert "client.set_config" in base


def test_no_api_key_is_offered_as_an_entity():
    """The warren refuses to write them over HTTP, so an entity for one would
    be a control that cannot work — and a secret in a dashboard besides."""
    forbidden = {"llm_key", "stt_key", "webhook_token"}
    offered = {row["key"] for _, row in ROWS}
    assert not (offered & forbidden), offered & forbidden
