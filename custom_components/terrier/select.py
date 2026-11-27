"""The nose, and every setting that is a choice from a short list."""

from __future__ import annotations

from typing import ClassVar

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import TerrierConfigEntry
from .api import TerrierError
from .brain import CHARACTERS
from .config_entity import TerrierSetting
from .const import NOSE_MODES, canon
from .entity import TerrierEntity, add_per_rabbit
from .settings import SELECTS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    add_per_rabbit(
        entry,
        async_add_entities,
        lambda c, mac, _r: [
            TerrierNose(c, mac),
            TerrierMind(c, mac),
            *(TerrierSettingSelect(c, mac, s) for s in SELECTS),
        ],
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
    heard of is refused at the other end. `contract/` compares this list with
    what `/api/rabbits/<mac>/settings` declares (review of 2026-11-18: the
    docstring promised that test and none existed; `sky` and `orange` were
    offered and refused).
    """

    def __init__(self, coordinator, mac: str, setting) -> None:
        super().__init__(coordinator, mac, setting)
        self._attr_options = list(setting.options)

    @property
    def current_option(self) -> str | None:
        v = self.value
        if self._setting.key == "nightlight_colour":
            # A colour saved under an older name is the one the belly shows.
            v = canon(v)
        return v if v in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        await self.write(option)


class TerrierMind(TerrierEntity, SelectEntity, RestoreEntity):
    """Its mind's character (brain.py): off, discreet, chatty, mischievous.

    Kept in Home Assistant alone, like everything the mind sees: the Terrier
    never learns it (Clara, 2026-11-27: the members' homes stay at home).
    Off until chosen, and the mind runs only when turned on in the options.
    """

    _attr_translation_key = "mind"
    _attr_options: ClassVar[list[str]] = list(CHARACTERS)

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "mind")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in CHARACTERS:
            self.coordinator.minds[self._mac] = last.state

    @property
    def current_option(self) -> str:
        return self.coordinator.minds.get(self._mac, "off")

    async def async_select_option(self, option: str) -> None:
        self.coordinator.minds[self._mac] = option
        self.async_write_ha_state()
