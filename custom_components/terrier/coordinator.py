"""One poll for the whole warren.

Every entity of every rabbit reads from this. A Nabaztag answers over a 2006
802.11b radio and the Terrier holds most of this in memory anyway, so the
expensive thing is not the data — it is asking for it once per entity. One
coordinator, one listing per cycle, and the rest of each rabbit now and then.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TerrierAuthError, TerrierClient, TerrierError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SLOW_INTERVAL

_LOGGER = logging.getLogger(__name__)


class TerrierCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Keeps every rabbit in the warren up to date, keyed by MAC."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: TerrierClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        # Per rabbit: the slow half (diagnostics, mood, mail) and when it was
        # last fetched, on the monotonic clock.
        self._slow: dict[str, dict[str, Any]] = {}
        self._slow_at: dict[str, float] = {}

    def _slow_due(self, mac: str, config: dict[str, Any], now: float) -> bool:
        if mac not in self._slow_at:
            return True
        if now - self._slow_at[mac] >= SLOW_INTERVAL.total_seconds():
            return True
        # The mood turned on since the last fetch: fetch it now, so the
        # sensor appears with the switch rather than five minutes later.
        mood = self._slow.get(mac, {}).get("mood") or {}
        return bool(config.get("tamagotchi_enabled")) and not mood.get("enabled")

    async def _fetch_slow(self, mac: str, config: dict[str, Any]) -> dict[str, Any]:
        detail = await self.client.rabbit(mac)
        # Only what the listing lacks. Not `last_ip`: nothing shows it any
        # more, and an owner's address has no business in Home Assistant's
        # memory (review of 2026-11-18).
        slow: dict[str, Any] = {"diagnostics": detail.get("diagnostics")}
        # The mood is a separate opt-in: a rabbit without one is not asked.
        if config.get("tamagotchi_enabled"):
            try:
                slow["mood"] = await self.client.mood(mac)
            except TerrierAuthError:
                raise
            except TerrierError:
                slow["mood"] = {"enabled": False}
        else:
            slow["mood"] = {"enabled": False}
        try:
            slow["mail"] = await self.client.mail(mac)
        except TerrierAuthError:
            raise
        except TerrierError:
            slow["mail"] = {"waiting": []}
        return slow

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            listing = await self.client.rabbits()
        except TerrierAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TerrierError as err:
            raise UpdateFailed(str(err)) from err

        rows = {r["mac"]: r for r in listing if isinstance(r.get("mac"), str)}
        now = time.monotonic()

        async def one(mac: str) -> None:
            config = rows[mac].get("config") or {}
            if not self._slow_due(mac, config, now):
                return
            try:
                self._slow[mac] = await self._fetch_slow(mac, config)
                self._slow_at[mac] = now
            except TerrierAuthError:
                raise
            except TerrierError as err:
                # One rabbit, not the warren. Review of 2026-11-18: a 404 on
                # one rabbit (unpaired between the listing and its detail)
                # failed the whole update and made every rabbit unavailable.
                # It keeps what it had and is asked again next cycle.
                _LOGGER.debug("rabbit …%s: %s", mac[-4:], err)

        try:
            await asyncio.gather(*(one(mac) for mac in rows))
        except TerrierAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err

        for gone in set(self._slow) - set(rows):
            self._slow.pop(gone, None)
            self._slow_at.pop(gone, None)
        # The listing wins: it is fresh every cycle, and its `online` is the
        # warren's whole rule — the detail's left out the Nabaztag v1, which
        # has no XMPP session (review of 2026-11-18: a v1 was never
        # "breathing").
        return {mac: {**self._slow.get(mac, {}), **row} for mac, row in rows.items()}

    def rabbit(self, mac: str) -> dict[str, Any]:
        return (self.data or {}).get(mac, {})


def stale_devices(
    devices: Iterable[Any],
    present: Iterable[str],
    missing_since: dict[str, float],
    now: float,
    grace: float,
) -> list[Any]:
    """The devices whose rabbit has left the listing for longer than `grace`.

    Review of 2026-11-18: a rabbit unpaired or given away stayed as an
    unavailable device forever. Not on the first poll that misses it: a
    warren that answers half a listing once must not cost an owner the
    names and areas they gave their entities.
    """
    present = set(present)
    out = []
    for device in devices:
        mac = next((i[1] for i in device.identifiers if i[0] == DOMAIN), None)
        if mac is None:
            continue
        if mac in present:
            missing_since.pop(mac, None)
            continue
        first = missing_since.setdefault(mac, now)
        if now - first >= grace:
            out.append(device)
    return out
