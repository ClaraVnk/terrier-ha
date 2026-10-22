"""The hours a rabbit keeps.

A Nabaztag's schedule is the half of it an automation most wants to reach:
when the morning weather is read out, when the alarm goes off, between which
hours the chime is allowed to speak. The Terrier stores each one as HH:MM,
which is exactly a `time` entity, so this platform is almost all table.

Seconds are dropped on the way in and zero on the way out — the warren's
scheduler ticks on the minute and would ignore them anyway, and a time
entity that silently rounded would be worse than one that says so here.
"""

from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TerrierConfigEntry
from .config_entity import TerrierSetting
from .settings import TIMES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TerrierSettingTime(coordinator, mac, setting)
        for mac in coordinator.data or {}
        for setting in TIMES
    )


class TerrierSettingTime(TerrierSetting, TimeEntity):
    """One HH:MM setting."""

    @property
    def native_value(self) -> dt_time | None:
        raw = self.value
        if not isinstance(raw, str):
            return None
        try:
            hour, minute = (int(part) for part in raw.split(":", 1))
            return dt_time(hour=hour, minute=minute)
        except (TypeError, ValueError):
            # A value the warren would not have written. Showing nothing is
            # better than showing midnight as though somebody had chosen it.
            return None

    async def async_set_value(self, value: dt_time) -> None:
        await self.write(f"{value.hour:02d}:{value.minute:02d}")
