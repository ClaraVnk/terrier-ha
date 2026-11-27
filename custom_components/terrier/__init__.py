"""Le Terrier — a Nabaztag:tag v2, in Home Assistant.

The rabbit itself speaks a 2006 protocol over plain HTTP and XMPP and cannot
be talked to directly; Le Terrier holds the connection and this integration
talks to it. Le Terrier is a hosted service: its code runs only on its own
server. For a rabbit kept entirely on the local network, the Home Assistant
add-on of ClaraVnk/nabaztag is the other way, and this does not talk to it.
"""

from __future__ import annotations

import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import TerrierClient
from .brain import Mind
from .const import CONF_BASE_URL, CONF_BRAIN, CONF_TOKEN, DOMAIN, SLOW_INTERVAL
from .coordinator import TerrierCoordinator, stale_devices
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

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type TerrierConfigEntry = ConfigEntry[TerrierCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """The actions, once for the integration.

    Here rather than with the entry: review of 2026-11-18, an entry that
    failed to load at boot (the warren down for a minute) left no
    `terrier.*` actions at all, and every automation using one failed its
    validation instead of reporting a rabbit it could not reach.
    """
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TerrierConfigEntry) -> bool:
    client = TerrierClient(
        async_get_clientsession(hass),
        entry.data[CONF_BASE_URL],
        entry.data[CONF_TOKEN],
    )
    coordinator = TerrierCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    missing_since: dict[str, float] = {}

    @callback
    def _prune() -> None:
        """Remove the device of a rabbit that has left the account."""
        if not coordinator.last_update_success or not coordinator.data:
            return
        registry = dr.async_get(hass)
        for device in stale_devices(
            dr.async_entries_for_config_entry(registry, entry.entry_id),
            coordinator.data,
            missing_since,
            time.monotonic(),
            SLOW_INTERVAL.total_seconds() * 2,
        ):
            registry.async_update_device(
                device.id, remove_config_entry_id=entry.entry_id
            )

    entry.async_on_unload(coordinator.async_add_listener(_prune))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if entry.options.get(CONF_BRAIN):
        entry.async_on_unload(Mind(hass, entry, coordinator).start())
    entry.async_on_unload(entry.add_update_listener(_options_changed))
    return True


async def _options_changed(hass: HomeAssistant, entry: TerrierConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: TerrierConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: TerrierConfigEntry, device: dr.DeviceEntry
) -> bool:
    """A rabbit no longer on the account may be deleted by hand."""
    data = getattr(entry, "runtime_data", None)
    present = set(data.data or {}) if data is not None else set()
    return not any(i[0] == DOMAIN and i[1] in present for i in device.identifiers)
