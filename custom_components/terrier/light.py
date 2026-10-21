"""The belly, as a light.

A Nabaztag's belly is not an RGB bulb: the nightlight takes one of seven
named colours and one of five levels. Exposing it as a full colour light
would let Home Assistant ask for a teal it cannot show, so this snaps whatever
colour it is given to the nearest one the rabbit actually has, and reports
back the colour it really used. A light that quietly lies about its state is
worse than one with seven colours.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .api import TerrierError
from .const import COLOURS
from .entity import TerrierEntity

# Five levels, as Home Assistant's 0-255 brightness. The rabbit's LED is not
# linear and the Terrier settled on five steps for that reason.
LEVELS = {1: 31, 2: 64, 3: 115, 4: 179, 5: 255}


def nearest_colour(rgb: tuple[int, int, int]) -> str:
    """The rabbit's closest colour to the one asked for.

    Nearest in plain RGB distance. Not perceptually clever, and it does not
    need to be: with seven well-separated colours, anything fancier changes no
    answers and only adds a way to be wrong.
    """
    return min(COLOURS, key=lambda name: math.dist(COLOURS[name], rgb))


def nearest_level(brightness: int) -> int:
    return min(LEVELS, key=lambda lvl: abs(LEVELS[lvl] - brightness))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TerrierNightlight(coordinator, mac) for mac in coordinator.data or {}
    )


class TerrierNightlight(TerrierEntity, LightEntity):
    _attr_translation_key = "nightlight"
    _attr_icon = "mdi:lightbulb-night"
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.RGB}

    def __init__(self, coordinator, mac: str) -> None:
        super().__init__(coordinator, mac, "nightlight")

    @property
    def is_on(self) -> bool:
        return bool(self.config.get("nightlight_on"))

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return COLOURS.get(
            self.config.get("nightlight_colour") or "warm", COLOURS["warm"]
        )

    @property
    def brightness(self) -> int:
        return LEVELS.get(int(self.config.get("nightlight_level") or 2), 64)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "colour": self.config.get("nightlight_colour") or "warm",
            "level": self.config.get("nightlight_level") or 2,
            "scheduled": bool(self.config.get("nightlight_enabled")),
            "from": self.config.get("nightlight_from"),
            "to": self.config.get("nightlight_to"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        colour = self.config.get("nightlight_colour") or "warm"
        level = int(self.config.get("nightlight_level") or 2)
        if ATTR_RGB_COLOR in kwargs:
            colour = nearest_colour(kwargs[ATTR_RGB_COLOR])
        if ATTR_BRIGHTNESS in kwargs:
            level = nearest_level(int(kwargs[ATTR_BRIGHTNESS]))
        try:
            await self.coordinator.client.nightlight(self._mac, True, colour, level)
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.client.nightlight(self._mac, False)
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
