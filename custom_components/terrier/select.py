"""The nose, as the three states the hardware can tell apart."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .api import TerrierError
from .const import NOSE_MODES
from .entity import TerrierEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(TerrierNose(coordinator, mac) for mac in coordinator.data or {})


class TerrierNose(TerrierEntity, SelectEntity):
    """Off, one blink, two blinks — and nothing else exists.

    The nose is driven by the waiting-message count, so selecting a mode here
    sets that count to 0, 1 or 2. They are the same register on the hardware,
    which is why this has three options and not a colour wheel.
    """

    _attr_translation_key = "nose"
    _attr_icon = "mdi:circle"
    _attr_options: ClassVar[list[str]] = list(NOSE_MODES)

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "nose")

    @property
    def current_option(self) -> str:
        n = int(self.config.get("counter") or 0)
        return "off" if n == 0 else "blink" if n == 1 else "double"

    async def async_select_option(self, option: str) -> None:
        try:
            await self.coordinator.client.nose(self._mac, option)
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
