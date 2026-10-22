"""Le Terrier — a Nabaztag:tag v2, in Home Assistant.

The rabbit itself speaks a 2006 protocol over plain HTTP and XMPP and cannot
be talked to directly; a Terrier holds the connection and this integration
talks to the Terrier. Point it at the hosted warren or at one you run
yourself — it is the same API either way.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TerrierClient
from .const import CONF_BASE_URL, CONF_TOKEN
from .coordinator import TerrierCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

type TerrierConfigEntry = ConfigEntry[TerrierCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TerrierConfigEntry) -> bool:
    client = TerrierClient(
        async_get_clientsession(hass),
        entry.data[CONF_BASE_URL],
        entry.data[CONF_TOKEN],
    )
    coordinator = TerrierCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TerrierConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: TerrierConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
