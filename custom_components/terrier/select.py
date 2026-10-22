"""The nose, and every setting that is a choice from a short list."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .api import TerrierError
from .config_entity import TerrierSetting
from .const import NOSE_MODES
from .entity import TerrierEntity
from .settings import SELECTS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    macs = list(coordinator.data or {})
    async_add_entities(
        [TerrierNose(coordinator, mac) for mac in macs]
        + [TerrierSettingSelect(coordinator, mac, setting)
           for mac in macs for setting in SELECTS]
    )


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


class TerrierSettingSelect(TerrierSetting, SelectEntity):
    """A setting whose values are a short fixed list.

    The options are the warren's own — a belly colour the firmware has never
    heard of is refused at the other end, and a test compares this list with
    what `/api/rabbits/<mac>/settings` declares.
    """

    def __init__(self, coordinator, mac: str, setting) -> None:
        super().__init__(coordinator, mac, setting)
        self._attr_options = list(setting.options)

    @property
    def current_option(self) -> str | None:
        v = self.value
        return v if v in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        await self.write(option)
