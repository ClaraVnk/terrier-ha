"""The base every Terrier entity shares.

One device per rabbit, named after what its owner called it. The MAC is the
unique id because it is the one thing about a Nabaztag that never changes —
not its name, not its address, not which warren it is pointed at.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TerrierCoordinator


@callback
def add_per_rabbit(
    entry: ConfigEntry,
    async_add_entities: Callable[[list[Entity]], None],
    build: Callable[[TerrierCoordinator, str, dict[str, Any]], Iterable[Entity]],
) -> None:
    """Add each rabbit's entities now, and again whenever a poll brings more.

    Review of 2026-11-18: every platform built its entities from the first
    poll only, so a rabbit adopted later never appeared without a reload, and
    the mood sensor never appeared if the mood was turned on afterwards.
    `build` says what a rabbit has *now*; only what is new gets added.
    """
    coordinator: TerrierCoordinator = entry.runtime_data
    known: dict[str, set[str]] = {}

    @callback
    def _add() -> None:
        data = coordinator.data or {}
        for gone in set(known) - set(data):
            # Forgotten, so a rabbit that comes back is added again.
            known.pop(gone)
        new: list[Entity] = []
        for mac, rabbit in data.items():
            seen = known.setdefault(mac, set())
            for entity in build(coordinator, mac, rabbit):
                if entity.unique_id not in seen:
                    seen.add(entity.unique_id)
                    new.append(entity)
        if new:
            async_add_entities(new)

    _add()
    entry.async_on_unload(coordinator.async_add_listener(_add))


class TerrierEntity(CoordinatorEntity[TerrierCoordinator]):
    """A thing belonging to one rabbit."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TerrierCoordinator, mac: str, key: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{mac}_{key}"

    @property
    def rabbit(self) -> dict[str, Any]:
        return self.coordinator.rabbit(self._mac)

    @property
    def config(self) -> dict[str, Any]:
        return self.rabbit.get("config") or {}

    @property
    def online(self) -> bool:
        return bool(self.rabbit.get("online"))

    @property
    def device_info(self) -> DeviceInfo:
        r = self.rabbit
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=r.get("name") or f"Nabaztag {self._mac[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=r.get("fw_version"),
            configuration_url=f"{self.coordinator.client.base_url}/rabbit/{self._mac}",
            # The registry's own MAC form, so the rabbit merges with what the
            # router's integration knows of it (review of 2026-11-18).
            connections={(CONNECTION_NETWORK_MAC, format_mac(self._mac))},
        )

    @property
    def available(self) -> bool:
        """Available means the WARREN answered about this rabbit.

        Not "the rabbit is plugged in": a rabbit that is unplugged still has a
        mood, a counter and a night schedule worth showing, and marking every
        entity unavailable the moment somebody pulls the plug would throw away
        the history that explains why.
        """
        return super().available and self._mac in (self.coordinator.data or {})
