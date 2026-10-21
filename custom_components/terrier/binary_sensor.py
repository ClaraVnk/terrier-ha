"""Is the rabbit there?

"Breathing" is Violet's word and the owners' word, and it means something more
precise than "online": the rabbit has finished its XMPP handshake and will
act on what it is sent. A rabbit that is powered on but stuck mid-boot is not
breathing, and this says so.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .entity import TerrierEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TerrierBreathing(coordinator, mac) for mac in coordinator.data or {}
    )


class TerrierBreathing(TerrierEntity, BinarySensorEntity):
    _attr_translation_key = "breathing"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "breathing")

    @property
    def is_on(self) -> bool:
        return self.online

    @property
    def extra_state_attributes(self) -> dict:
        r = self.rabbit
        return {
            "last_seen": r.get("last_seen"),
            "firmware": r.get("fw_version"),
            "ip": r.get("last_ip"),
        }
