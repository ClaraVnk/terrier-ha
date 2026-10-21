"""The base every Terrier entity shares.

One device per rabbit, named after what its owner called it. The MAC is the
unique id because it is the one thing about a Nabaztag that never changes —
not its name, not its address, not which warren it is pointed at.
"""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TerrierCoordinator


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
            connections={("mac", self._mac)},
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
