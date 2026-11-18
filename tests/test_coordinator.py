"""The poll: what it asks for, how often, and what one bad rabbit costs.

The client is a fake that counts; the coordinator is the real one, on the
Home Assistant stand-ins of hastub. Findings of the review of 2026-11-18.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace

import hastub
import pytest

from custom_components.terrier import api, const, coordinator

DOMAIN = const.DOMAIN
# Read, not imported: on the code the review found, this did not exist and
# each test should fail on its own finding rather than all on an import.
SLOW_INTERVAL = getattr(const, "SLOW_INTERVAL", timedelta(minutes=5))

A, B = "0019dbdeadbe", "0019dbfeed11"


class FakeClient:
    def __init__(self, macs=(A, B)) -> None:
        self.macs = list(macs)
        self.calls: list[tuple[str, str]] = []
        self.broken: set[str] = set()
        self.auth_broken = False
        self.config: dict[str, dict] = {}
        self.listing_online = True

    async def rabbits(self):
        self.calls.append(("rabbits", ""))
        return [
            {
                "mac": m,
                "name": f"r{m[-2:]}",
                "online": self.listing_online,
                "config": self.config.get(m, {}),
            }
            for m in self.macs
        ]

    async def rabbit(self, mac):
        self.calls.append(("rabbit", mac))
        if self.auth_broken:
            raise api.TerrierAuthError("refused")
        if mac in self.broken:
            raise api.TerrierError("not found")
        # The detail as the warren of 2026-11-18 had it: `online` without the
        # Nabaztag v1 rule, so False where the listing says True.
        return {"mac": mac, "online": False, "diagnostics": {"boots": 1}}

    async def mood(self, mac):
        self.calls.append(("mood", mac))
        return {"enabled": True, "mood": 70}

    async def mail(self, mac):
        self.calls.append(("mail", mac))
        return {"handle": "h", "waiting": []}


def _coordinator(client):
    return coordinator.TerrierCoordinator(None, None, client)


def _poll(c):
    data = asyncio.run(c._async_update_data())
    c.data = data
    return data


# --- M3 ---------------------------------------------------------------------
def test_one_rabbit_failing_does_not_blank_the_others():
    client = FakeClient()
    client.broken.add(B)
    data = _poll(_coordinator(client))
    assert data[A]["diagnostics"] == {"boots": 1}
    assert B in data, "a rabbit in the listing stays, with what the listing says"


def test_a_rabbit_that_fails_later_keeps_what_it_had(monkeypatch):
    client = FakeClient()
    c = _coordinator(client)
    _poll(c)
    client.broken.add(B)
    monkeypatch.setattr(coordinator, "time", SimpleNamespace(monotonic=lambda: 1e12))
    data = _poll(c)
    assert data[B]["diagnostics"] == {"boots": 1}


def test_a_refused_token_is_still_a_reauth():
    client = FakeClient()
    client.auth_broken = True
    with pytest.raises(hastub.ConfigEntryAuthFailed):
        _poll(_coordinator(client))


# --- M2 ---------------------------------------------------------------------
def test_online_is_the_listings():
    """The listing's `online` counts a v1 seen in the last two minutes; the
    detail's did not, and the coordinator kept the detail's."""
    data = _poll(_coordinator(FakeClient()))
    assert data[A]["online"] is True


# --- H3, M5 -----------------------------------------------------------------
def test_a_poll_inside_five_minutes_is_one_request():
    client = FakeClient()
    c = _coordinator(client)
    _poll(c)
    client.calls.clear()
    _poll(c)
    assert client.calls == [("rabbits", "")]


def test_after_five_minutes_the_rest_comes_back(monkeypatch):
    client = FakeClient()
    c = _coordinator(client)
    _poll(c)
    client.calls.clear()
    later = coordinator.time.monotonic() + SLOW_INTERVAL.total_seconds() + 1
    monkeypatch.setattr(coordinator, "time", SimpleNamespace(monotonic=lambda: later))
    _poll(c)
    assert ("mail", A) in client.calls
    assert ("rabbit", B) in client.calls


def test_the_mood_is_asked_for_only_when_it_is_on_and_at_once():
    client = FakeClient(macs=(A,))
    c = _coordinator(client)
    data = _poll(c)
    assert ("mood", A) not in client.calls
    assert data[A]["mood"] == {"enabled": False}
    client.config[A] = {"tamagotchi_enabled": True}
    data = _poll(c)
    assert ("mood", A) in client.calls
    assert data[A]["mood"]["enabled"] is True


def test_a_rabbit_that_left_the_listing_leaves_the_data():
    client = FakeClient()
    c = _coordinator(client)
    _poll(c)
    client.macs.remove(B)
    assert set(_poll(c)) == {A}


# --- M7 ---------------------------------------------------------------------
def _device(mac):
    return SimpleNamespace(id=f"dev-{mac}", identifiers={(DOMAIN, mac)})


def test_a_device_goes_only_after_its_rabbit_has_been_gone_a_while():
    missing: dict[str, float] = {}
    devices = [_device(A), _device(B)]
    assert coordinator.stale_devices(devices, {A}, missing, 0.0, 600) == []
    assert coordinator.stale_devices(devices, {A}, missing, 599.0, 600) == []
    gone = coordinator.stale_devices(devices, {A}, missing, 600.0, 600)
    assert [d.id for d in gone] == [f"dev-{B}"]


def test_a_rabbit_back_in_time_keeps_its_device():
    missing: dict[str, float] = {}
    devices = [_device(B)]
    coordinator.stale_devices(devices, set(), missing, 0.0, 600)
    coordinator.stale_devices(devices, {B}, missing, 300.0, 600)
    assert coordinator.stale_devices(devices, set(), missing, 700.0, 600) == []
