"""Everything that has to agree with everything else.

A custom integration fails in three ways that no amount of care at the
keyboard prevents: a service declared in one file and forgotten in another, a
translation that drifts, and a manifest key that a newer Home Assistant
started requiring. These are cheap to check and expensive to discover from a
user's log.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "terrier"


def load(name: str):
    return json.loads((COMPONENT / name).read_text())


def test_the_manifest_has_what_hassfest_requires():
    m = load("manifest.json")
    for key in (
        "domain",
        "name",
        "codeowners",
        "documentation",
        "iot_class",
        "version",
        "config_flow",
        "integration_type",
    ):
        assert key in m, key
    assert m["domain"] == "terrier"
    assert m["config_flow"] is True
    assert m["requirements"] == [], (
        "this integration ships no dependency of its own — keep it that way"
    )


def test_hacs_declares_the_minimum_home_assistant():
    h = json.loads((ROOT / "hacs.json").read_text())
    assert h["content_in_root"] is False
    assert "homeassistant" in h


def _services_in_yaml() -> set[str]:
    return set(yaml.safe_load((COMPONENT / "services.yaml").read_text()))


def _services_registered() -> set[str]:
    """The names services.py actually registers, read out of the source.

    From the registration loop rather than from the constants: a constant that
    nothing registers is exactly the bug this is looking for.
    """
    tree = ast.parse((COMPONENT / "services.py").read_text())
    const = ast.parse((COMPONENT / "const.py").read_text())
    names = {}
    for node in ast.walk(const):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.startswith("SERVICE_"):
                    names[t.id] = node.value.value
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 3:
            first = node.elts[0]
            if isinstance(first, ast.Name) and first.id in names:
                found.add(names[first.id])
    return found


def test_every_service_is_declared_registered_and_described():
    in_yaml = _services_in_yaml()
    registered = _services_registered()
    described = set(load("strings.json")["services"])
    assert registered == in_yaml, (
        f"registered but not in services.yaml: {sorted(registered - in_yaml)}; "
        f"declared but never registered: {sorted(in_yaml - registered)}"
    )
    assert registered == described, (
        f"no description for: {sorted(registered - described)}"
    )


def test_every_service_field_is_described():
    spec = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    strings = load("strings.json")["services"]
    missing = []
    for name, body in spec.items():
        fields = set((body or {}).get("fields") or {})
        described = set(strings[name].get("fields") or {})
        missing += [f"{name}.{f}" for f in fields - described]
    assert not missing, missing


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_translation_matches_the_strings_exactly(lang):
    """A missing key shows the reader a raw identifier; an extra one is dead
    weight that hides the missing ones."""

    def keys(d, prefix=""):
        out = set()
        for k, v in d.items():
            p = f"{prefix}.{k}" if prefix else k
            out.add(p)
            if isinstance(v, dict):
                out |= keys(v, p)
        return out

    base = keys(load("strings.json"))
    other = keys(json.loads((COMPONENT / "translations" / f"{lang}.json").read_text()))
    assert base == other, (
        f"missing in {lang}: {sorted(base - other)}; "
        f"extra in {lang}: {sorted(other - base)}"
    )


def test_every_entity_has_a_name_and_an_icon():
    strings = load("strings.json")["entity"]
    icons = load("icons.json")["entity"]
    for platform, entities in strings.items():
        assert platform in icons, f"no icons for {platform}"
        for key in entities:
            assert key in icons[platform], f"{platform}.{key} has no icon"


def test_the_platforms_listed_in_init_all_exist():
    tree = ast.parse((COMPONENT / "__init__.py").read_text())
    platforms = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "Platform"
        ):
            platforms.add(node.attr.lower())
    assert platforms, "no platforms found — did PLATFORMS move?"
    for p in platforms:
        assert (COMPONENT / f"{p}.py").is_file(), f"{p}.py is missing"
