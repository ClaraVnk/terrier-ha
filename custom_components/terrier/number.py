"""The counter, as a number you can set from an automation.

This is Violet's unread-message count, and on the hardware it is the nose:
violet, one blink at one, two blinks at two and above. There is no digit
anywhere on a Nabaztag. Point it at parcels, open tickets, days until the
holidays — the Terrier lets its owner name it, and the name shows up here.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .api import TerrierError
from .entity import TerrierEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TerrierCounter(coordinator, mac) for mac in coordinator.data or {}
    )


class TerrierCounter(TerrierEntity, NumberEntity):
    _attr_translation_key = "counter"
    _attr_icon = "mdi:numeric"
    _attr_native_min_value = 0
    _attr_native_max_value = 255
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "counter_set")

    @property
    def native_value(self) -> float:
        return float(self.config.get("counter") or 0)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "label": self.config.get("counter_label") or "",
            "nose": "off"
            if not self.config.get("counter")
            else "one blink"
            if self.config.get("counter") == 1
            else "two blinks",
        }

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.coordinator.client.counter(self._mac, int(value))
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
