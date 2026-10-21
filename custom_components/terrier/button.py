"""The things you press once."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .api import TerrierClient, TerrierError, TerrierOffline
from .entity import TerrierEntity


@dataclass(frozen=True, kw_only=True)
class TerrierButton(ButtonEntityDescription):
    press: Callable[[TerrierClient, str], Awaitable]
    needs_rabbit: bool = True


BUTTONS: tuple[TerrierButton, ...] = (
    TerrierButton(
        key="compliment",
        translation_key="compliment",
        icon="mdi:heart-outline",
        press=lambda c, mac: c.compliment(mac),
    ),
    TerrierButton(
        key="stop",
        translation_key="stop",
        icon="mdi:stop",
        press=lambda c, mac: c.radio(mac, stop=True),
    ),
    TerrierButton(
        key="wake",
        translation_key="wake",
        icon="mdi:weather-sunset-up",
        press=lambda c, mac: c.sleep(mac, False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TerrierButtonEntity(coordinator, mac, desc)
        for mac in coordinator.data or {}
        for desc in BUTTONS
    )


class TerrierButtonEntity(TerrierEntity, ButtonEntity):
    entity_description: TerrierButton

    def __init__(self, coordinator, mac: str, desc: TerrierButton) -> None:
        super().__init__(coordinator, mac, desc.key)
        self.entity_description = desc

    async def async_press(self) -> None:
        try:
            await self.entity_description.press(self.coordinator.client, self._mac)
        except TerrierOffline as err:
            # Not a broken integration — somebody unplugged a rabbit. Saying
            # so plainly beats a traceback in the log.
            raise HomeAssistantError(
                f"{self.name}: the rabbit is not connected ({err})"
            ) from err
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
