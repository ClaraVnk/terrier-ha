"""One poll for the whole warren.

Every entity of every rabbit reads from this. A Nabaztag answers over a 2006
802.11b radio and the Terrier holds most of this in memory anyway, so the
expensive thing is not the data — it is asking for it once per entity. One
coordinator, one request per rabbit per cycle.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TerrierAuthError, TerrierClient, TerrierError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

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
        self.jingles: list[str] = []

    async def _async_setup(self) -> None:
        """Fetch the things that do not change between polls."""
        try:
            self.jingles = await self.client.jingles()
        except TerrierError as err:  # not fatal: it is a list of names
            _LOGGER.debug("could not list jingles: %s", err)

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            listing = await self.client.rabbits()
        except TerrierAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TerrierError as err:
            raise UpdateFailed(str(err)) from err

        async def one(mac: str) -> tuple[str, dict[str, Any]]:
            data = await self.client.rabbit(mac)
            # The mood is a separate call because it is a separate opt-in: a
            # rabbit without one answers {"enabled": false} and that is not an
            # error, so a failure here must not lose the rest of the rabbit.
            try:
                data["mood"] = await self.client.mood(mac)
            except TerrierError:
                data["mood"] = {"enabled": False}
            try:
                data["mail"] = await self.client.mail(mac)
            except TerrierError:
                data["mail"] = {"waiting": []}
            return mac, data

        try:
            results = await asyncio.gather(
                *(one(r["mac"]) for r in listing if r.get("mac"))
            )
        except TerrierAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TerrierError as err:
            raise UpdateFailed(str(err)) from err
        return dict(results)

    def rabbit(self, mac: str) -> dict[str, Any]:
        return (self.data or {}).get(mac, {})
