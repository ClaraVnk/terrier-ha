"""The half of a rabbit that is a setting rather than an action.

Every entity built from `settings.py` reads one key out of the config the
coordinator already polls, and writes it back with one call. The warren
applies a settings patch all-or-nothing, so a write that returns without
raising really did land — there is no half-applied state to reconcile.
"""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .api import TerrierError
from .entity import TerrierEntity
from .settings import Setting


class TerrierSetting(TerrierEntity):
    """One config key on one rabbit."""

    def __init__(self, coordinator, mac: str, setting: Setting) -> None:
        super().__init__(coordinator, mac, setting.key)
        self._setting = setting
        self._attr_translation_key = setting.key
        self._attr_icon = setting.icon
        self._attr_entity_category = setting.category
        self._attr_entity_registry_enabled_default = setting.enabled

    @property
    def value(self) -> Any:
        return self.config.get(self._setting.key)

    async def write(self, value: Any) -> None:
        try:
            await self.coordinator.client.set_config(
                self._mac, **{self._setting.key: value}
            )
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
