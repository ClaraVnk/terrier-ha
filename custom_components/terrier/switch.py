"""What a rabbit does on its own, turned on and off."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .api import TerrierError
from .config_entity import TerrierSetting
from .entity import TerrierEntity
from .settings import SWITCHES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    macs = list(coordinator.data or {})
    async_add_entities(
        [
            cls(coordinator, mac)
            for mac in macs
            for cls in (TerrierSleep, TerrierMailbox)
        ]
        + [
            TerrierSettingSwitch(coordinator, mac, setting)
            for mac in macs
            for setting in SWITCHES
        ]
    )


class TerrierSleep(TerrierEntity, SwitchEntity):
    """Hardware sleep: lights out, ears down, pushed commands refused.

    On means ASLEEP, which is the opposite of how most switches read. It is
    named "Sleep" rather than "Awake" because that is the rabbit's own state
    and the word the Terrier uses; calling it Awake would invert the Terrier's
    own page and make the two disagree.
    """

    _attr_translation_key = "sleep"
    _attr_icon = "mdi:sleep"

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "sleep")

    @property
    def is_on(self) -> bool:
        return bool(self.config.get("night_slept"))

    async def _set(self, asleep: bool) -> None:
        try:
            await self.coordinator.client.sleep(self._mac, asleep)
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)


class TerrierMailbox(TerrierEntity, SwitchEntity):
    """Whether other rabbits may write to this one.

    Read-only to the Terrier's own setting rather than something this
    integration can switch on: opening a device in somebody's living room to
    strangers is a decision that belongs on the warren's page, next to the
    sentence explaining what it means — not behind a toggle in an automation.
    """

    _attr_translation_key = "mailbox"
    _attr_icon = "mdi:mailbox"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "mailbox")

    @property
    def is_on(self) -> bool:
        return bool(self.config.get("mail_enabled"))

    @property
    def available(self) -> bool:
        return super().available

    async def async_turn_on(self, **kwargs: Any) -> None:
        raise HomeAssistantError(
            "Opening a rabbit's postbox is done on the Terrier, where the "
            "handle and the blocklist are"
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        raise HomeAssistantError("Closing a rabbit's postbox is done on the Terrier")


class TerrierSettingSwitch(TerrierSetting, SwitchEntity):
    """A yes-or-no setting: the morning weather, the alarm, the chime.

    These are what the integration was missing — not verbs the rabbit
    performs but the schedule it keeps, which is exactly the half an
    automation wants to reach for.
    """

    @property
    def is_on(self) -> bool:
        return bool(self.value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.write(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.write(False)
