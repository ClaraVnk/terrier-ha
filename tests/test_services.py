"""The actions, from the handler Home Assistant calls down to the request.

Registered on a stand-in `hass`, called with a stand-in ServiceCall, aimed at
rabbits through `_targets` replaced by a list. The client is the real one on
a session that records. Findings of the review of 2026-11-18.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import hastub
import pytest

from custom_components.terrier import api, services

A, B = "0019dbdeadbe", "0019dbfeed11"


class Session:
    """aiohttp-shaped. `fail` maps a path fragment to (status, body)."""

    def __init__(self, fail: dict[str, tuple[int, Any]] | None = None) -> None:
        self.sent: list[tuple[str, str, Any]] = []
        self.fail = fail or {}
        self._next: tuple[int, Any] = (200, {})

    def request(self, method, url, json=None, **_kw):
        path = str(url).split("example.com", 1)[1]
        self.sent.append((method, path, json))
        self._next = next(
            (v for k, v in self.fail.items() if k in path), (200, {"ok": True})
        )
        return self

    async def __aenter__(self):
        self.status = self._next[0]
        return self

    async def __aexit__(self, *exc):
        return False

    content_type = "application/json"

    async def json(self):
        return self._next[1]


class Coordinator:
    def __init__(self, session: Session) -> None:
        self.client = api.TerrierClient(session, "https://example.com", "trr_x")
        self.refreshes = 0

    def rabbit(self, mac):
        return {"name": {A: "Nabi", B: "Zabou"}[mac]}

    async def async_request_refresh(self):
        self.refreshes += 1


class Services:
    def __init__(self) -> None:
        self.handlers: dict[str, Any] = {}

    def has_service(self, domain, name):
        return False

    def async_register(self, domain, name, handler, schema=None, **_kw):
        self.handlers[name] = (handler, schema)


@pytest.fixture
def call(monkeypatch):
    """call(name, data, session=..., macs=...) runs one action."""
    hass = SimpleNamespace(services=Services())
    services.async_setup_services(hass)

    def _call(name, data, session=None, macs=(A,)):
        session = session or Session()
        coord = Coordinator(session)
        monkeypatch.setattr(
            services, "_targets", lambda _h, _c: [(coord, m) for m in macs]
        )
        handler, schema = hass.services.handlers[name]
        data = schema({"device_id": ["dev"], **data})
        result = asyncio.run(handler(SimpleNamespace(data=data)))
        return session, result

    return _call


# --- H1 ---------------------------------------------------------------------
def test_jingle_action_names_the_jingle(call):
    session, _ = call("jingle", {"jingle": "bip"})
    assert session.sent == [("POST", f"/api/rabbits/{A}/jingle", {"name": "bip"})]


# --- H2 ---------------------------------------------------------------------
def test_ambient_colour_is_the_breathing_colour_setting(call):
    """`/ambient` wants a raw service byte; the colour the belly breathes in
    is the `breath_colour` setting. An older name is the colour it shows."""
    session, _ = call("ambient", {"colour": "sky"})
    assert session.sent == [
        ("POST", f"/api/rabbits/{A}/config", {"breath_colour": "cyan"})
    ]


def test_ambient_clear_clears_the_belly(call):
    session, _ = call("ambient", {"clear": True})
    assert session.sent == [("POST", f"/api/rabbits/{A}/belly/clear", {})]


# --- M1 ---------------------------------------------------------------------
def test_notify_takes_the_palette_and_the_older_names(call):
    for colour in ("cyan", "yellow", "red", "warm"):
        session, _ = call("notify", {"colour": colour})
        assert session.sent[0][2]["colour"] == colour


# --- L1, H4 -----------------------------------------------------------------
def test_set_config_with_a_key_called_mac(call):
    session, _ = call("set_config", {"settings": {"mac": "x"}})
    assert session.sent == [("POST", f"/api/rabbits/{A}/config", {"mac": "x"})]


def test_set_config_will_not_choose_the_bytecode(call):
    with pytest.raises(hastub.ServiceValidationError):
        call("set_config", {"settings": {"bytecode": "experimental"}})


# --- L6 ---------------------------------------------------------------------
def test_every_rabbit_is_tried_and_the_failures_are_named(call):
    session = Session(fail={A: (503, {"error": "rabbit offline"})})
    with pytest.raises(hastub.HomeAssistantError) as e:
        call("speak", {"text": "coucou"}, session=session, macs=(A, B))
    assert [p for _m, p, _j in session.sent] == [
        f"/api/rabbits/{A}/speak",
        f"/api/rabbits/{B}/speak",
    ]
    assert "Nabi" in str(e.value)
    assert "Zabou" not in str(e.value)


def test_a_question_keeps_the_answers_it_got(call):
    session = Session(fail={A: (503, {"error": "rabbit offline"})})
    _, result = call("ask", {"question": "?"}, session=session, macs=(A, B))
    assert B in result
    assert "Nabi" in result["errors"][0]


# --- L8 ---------------------------------------------------------------------
def test_podcast_takes_a_catalogue_key(call):
    session, _ = call("podcast", {"feed": "franceinter-lgdj"})
    assert session.sent[0][2]["feed"] == "franceinter-lgdj"
