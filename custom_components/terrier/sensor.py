"""What the warren knows about a rabbit, as numbers.

The diagnostics are the interesting half. A 2006 802.11b radio on a modern
access point drops connections, and the whole reason the Terrier keeps an
event log is so that "it stopped working" can become "it lost the server
eleven times yesterday and each session lasted four minutes".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TerrierConfigEntry
from .entity import TerrierEntity


@dataclass(frozen=True, kw_only=True)
class TerrierSensor(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]
    attrs: Callable[[dict[str, Any]], dict] | None = None


def _diag(rabbit: dict, key: str) -> Any:
    return (rabbit.get("diagnostics") or {}).get(key)


SENSORS: tuple[TerrierSensor, ...] = (
    TerrierSensor(
        key="availability",
        translation_key="availability",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda r: _diag(r, "availability_pct"),
    ),
    TerrierSensor(
        key="disconnects",
        translation_key="disconnects",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda r: _diag(r, "disconnects"),
        attrs=lambda r: {
            "boots": _diag(r, "boots"),
            "reconnects": _diag(r, "reconnects"),
        },
    ),
    TerrierSensor(
        key="session",
        translation_key="session",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda r: _diag(r, "avg_session_min"),
    ),
    TerrierSensor(
        key="rtt",
        translation_key="rtt",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda r: _diag(r, "rtt_median_ms"),
        attrs=lambda r: {"loss_pct": _diag(r, "loss_pct")},
    ),
    TerrierSensor(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda r: dt_util.parse_datetime(r["last_seen"])
        if r.get("last_seen")
        else None,
    ),
    TerrierSensor(
        key="waiting",
        translation_key="waiting",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda r: len((r.get("mail") or {}).get("waiting") or []),
        attrs=lambda r: {
            "from": [
                m.get("from_handle") for m in (r.get("mail") or {}).get("waiting") or []
            ],
            "handle": (r.get("mail") or {}).get("handle"),
        },
    ),
    TerrierSensor(
        key="mood",
        translation_key="mood",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda r: (r.get("mood") or {}).get("mood"),
        attrs=lambda r: {"band": (r.get("mood") or {}).get("band")},
    ),
    TerrierSensor(
        key="counter",
        translation_key="counter",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda r: (r.get("config") or {}).get("counter", 0),
        attrs=lambda r: {"label": (r.get("config") or {}).get("counter_label") or ""},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TerrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for mac, rabbit in (coordinator.data or {}).items():
        for desc in SENSORS:
            # The mood is opt-in per rabbit; an entity that is permanently
            # "unknown" is clutter, so it only appears once somebody asks for
            # a mood on the Terrier.
            if desc.key == "mood" and not (rabbit.get("mood") or {}).get("enabled"):
                continue
            entities.append(TerrierSensorEntity(coordinator, mac, desc))
    async_add_entities(entities)


class TerrierSensorEntity(TerrierEntity, SensorEntity):
    entity_description: TerrierSensor

    def __init__(self, coordinator, mac: str, desc: TerrierSensor) -> None:
        super().__init__(coordinator, mac, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        try:
            return self.entity_description.value(self.rabbit)
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attrs is None:
            return None
        try:
            return self.entity_description.attrs(self.rabbit)
        except (KeyError, TypeError, ValueError):
            return None
