"""Just enough of Home Assistant to import the integration and drive it.

The tests run without Home Assistant installed: CI installs pytest, pyyaml,
aiohttp and voluptuous, nothing more. Every name the integration imports
resolves here — most to an empty class, the few the code under test relies
on to something with the behaviour Home Assistant gives them: the
coordinator stores its data and calls its listeners, the exceptions are
exceptions, `callback` returns the function.

`import hastub` before importing anything from `custom_components`.
"""

from __future__ import annotations

import dataclasses
import enum
import sys
import types
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class _Meta(type):
    def __getattr__(cls, name: str) -> str:
        # `ColorMode.RGB`, `UnitOfTime.MINUTES`: a constant is its own name.
        if name.startswith("__"):
            raise AttributeError(name)
        return name


class _Base(metaclass=_Meta):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __class_getitem__(cls, _item: Any) -> type:
        return cls

    def __call__(self, value: Any) -> Any:
        # A selector is a validator in a voluptuous schema.
        return value

    def __init_subclass__(cls, **_kwargs: Any) -> None:
        # `class Flow(ConfigFlow, domain=DOMAIN)`
        super().__init_subclass__()


class _Module(types.ModuleType):
    """A module in which any name exists, as an empty class."""

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        cls = _Meta(name, (_Base,), {})
        setattr(self, name, cls)
        return cls


def _module(name: str, **attrs: Any) -> _Module:
    mod = sys.modules.get(name)
    if not isinstance(mod, _Module):
        mod = _Module(name)
        mod.__path__ = []  # a package, so submodules import
        sys.modules[name] = mod
        parent, _, child = name.rpartition(".")
        if parent:
            setattr(_module(parent), child, mod)
    mod.__dict__.update(attrs)
    return mod


# ------------------------------------------------------------- behaviour


class HomeAssistantError(Exception):
    pass


class ServiceValidationError(HomeAssistantError):
    pass


class ConfigEntryAuthFailed(Exception):
    pass


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator(_Base):
    def __init__(self, hass: Any, logger: Any, **kwargs: Any) -> None:
        self.hass = hass
        self.logger = logger
        self.data: Any = None
        self.last_update_success = True
        self.refreshes = 0
        self._listeners: list = []

    def async_add_listener(self, update: Any) -> Any:
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    def async_update_listeners(self) -> None:
        for update in list(self._listeners):
            update()

    async def async_request_refresh(self) -> None:
        self.refreshes += 1


class CoordinatorEntity(_Base):
    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator

    @property
    def unique_id(self) -> str | None:
        return getattr(self, "_attr_unique_id", None)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.last_update_success)

    @property
    def name(self) -> str | None:
        return getattr(self, "_attr_name", None)


@dataclasses.dataclass(frozen=True, kw_only=True)
class EntityDescription:
    key: str
    translation_key: str | None = None
    icon: str | None = None
    device_class: Any = None
    entity_category: Any = None
    native_unit_of_measurement: Any = None
    state_class: Any = None
    entity_registry_enabled_default: bool = True


class EntityCategory(enum.StrEnum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


def format_mac(mac: str) -> str:
    mac = mac.replace(":", "").replace("-", "").lower()
    return ":".join(mac[i : i + 2] for i in range(0, 12, 2))


def _identity(value: Any) -> Any:
    return value


def _ensure_list(value: Any) -> list:
    return value if isinstance(value, list) else [value]


def _url(value: Any) -> str:
    """Home Assistant's `cv.url`: an http(s) address or Invalid."""
    import voluptuous as vol

    if urlparse(str(value)).scheme not in ("http", "https"):
        raise vol.Invalid("invalid url")
    return str(value)


def install() -> None:
    _module("homeassistant")
    _module("homeassistant.core", callback=_identity)
    _module(
        "homeassistant.exceptions",
        HomeAssistantError=HomeAssistantError,
        ServiceValidationError=ServiceValidationError,
        ConfigEntryAuthFailed=ConfigEntryAuthFailed,
    )
    _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=DataUpdateCoordinator,
        UpdateFailed=UpdateFailed,
        CoordinatorEntity=CoordinatorEntity,
    )
    _module(
        "homeassistant.helpers.device_registry",
        DeviceInfo=dict,
        CONNECTION_NETWORK_MAC="mac",
        format_mac=format_mac,
    )
    _module("homeassistant.helpers.entity", EntityCategory=EntityCategory)
    _module("homeassistant.const", EntityCategory=EntityCategory)
    _module(
        "homeassistant.helpers.config_validation",
        string=str,
        boolean=bool,
        url=_url,
        ensure_list=_ensure_list,
        config_entry_only_config_schema=lambda domain: None,
    )
    for platform in ("sensor", "button"):
        _module(
            f"homeassistant.components.{platform}",
            **{f"{platform.capitalize()}EntityDescription": EntityDescription},
        )
    for name in (
        "homeassistant.config_entries",
        "homeassistant.components.binary_sensor",
        "homeassistant.components.light",
        "homeassistant.components.number",
        "homeassistant.components.select",
        "homeassistant.components.switch",
        "homeassistant.components.time",
        "homeassistant.helpers.aiohttp_client",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.selector",
        "homeassistant.helpers.typing",
        "homeassistant.util",
    ):
        _module(name)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


install()
