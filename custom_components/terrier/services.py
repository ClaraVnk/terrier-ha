"""The verbs: everything a rabbit does that is not a state to be toggled.

Targeted at devices rather than entities. "Speak" is not a property of the
belly light or the counter — it is something the rabbit does — and hanging it
off an arbitrary entity would make every automation read as though it were.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import TerrierError, TerrierOffline
from .const import (
    COLOURS,
    DOMAIN,
    NOSE_MODES,
    SERVICE_EARS,
    SERVICE_JINGLE,
    SERVICE_MAIL,
    SERVICE_NOTIFY,
    SERVICE_PODCAST,
    SERVICE_RADIO,
    SERVICE_SPEAK,
)

ATTR_DEVICE_ID = "device_id"

_TARGET = {vol.Required(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string])}

NOTIFY_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Optional("text"): cv.string,
        vol.Optional("colour"): vol.In(sorted(COLOURS)),
        vol.Optional("level"): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
        vol.Optional("jingle"): cv.string,
        vol.Optional("nose"): vol.In(NOSE_MODES),
        vol.Optional("counter"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)

SPEAK_SCHEMA = vol.Schema({**_TARGET, vol.Required("text"): cv.string})
JINGLE_SCHEMA = vol.Schema({**_TARGET, vol.Required("jingle"): cv.string})
RADIO_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Exclusive("station", "what"): cv.string,
        vol.Exclusive("stop", "what"): cv.boolean,
    }
)
PODCAST_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Optional("feed"): cv.url,
        vol.Optional("episode", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("stop", default=False): cv.boolean,
    }
)
EARS_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Required("left"): vol.All(vol.Coerce(int), vol.Range(min=0, max=16)),
        vol.Required("right"): vol.All(vol.Coerce(int), vol.Range(min=0, max=16)),
    }
)
MAIL_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Required("to"): cv.string,
        vol.Required("text"): vol.All(cv.string, vol.Length(max=200)),
        vol.Optional("jingle"): cv.string,
    }
)


def _targets(hass: HomeAssistant, call: ServiceCall) -> list[tuple]:
    """(coordinator, mac) for every rabbit the call is aimed at."""
    registry = dr.async_get(hass)
    found = []
    for device_id in call.data[ATTR_DEVICE_ID]:
        device = registry.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"unknown device {device_id}")
        mac = next((i[1] for i in device.identifiers if i[0] == DOMAIN), None)
        if mac is None:
            raise ServiceValidationError(f"{device.name} is not a rabbit on a Terrier")
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != DOMAIN:
                continue
            coordinator = getattr(entry, "runtime_data", None)
            if coordinator is None:
                # The entry exists but is not loaded — reloading, or failed at
                # startup. Saying so beats an AttributeError in the log.
                raise ServiceValidationError(
                    f"{device.name}: its Terrier is not loaded right now"
                )
            found.append((coordinator, mac))
            break
    if not found:
        raise ServiceValidationError("no rabbit in this call is set up")
    return found


async def _run(hass: HomeAssistant, call: ServiceCall, verb) -> None:
    for coordinator, mac in _targets(hass, call):
        try:
            await verb(coordinator.client, mac)
        except TerrierOffline as err:
            raise HomeAssistantError(f"the rabbit is not connected ({err})") from err
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Registered once for the whole integration, not once per entry."""
    if hass.services.has_service(DOMAIN, SERVICE_SPEAK):
        return

    async def speak(call: ServiceCall) -> None:
        await _run(hass, call, lambda c, mac: c.speak(mac, call.data["text"]))

    async def notify(call: ServiceCall) -> None:
        fields = {k: v for k, v in call.data.items() if k != ATTR_DEVICE_ID}
        if not fields:
            raise ServiceValidationError(
                "nothing to do: give it some text, a colour, a jingle, a nose "
                "or a counter"
            )
        await _run(hass, call, lambda c, mac: c.notify(mac, **fields))

    async def jingle(call: ServiceCall) -> None:
        await _run(hass, call, lambda c, mac: c.play_jingle(mac, call.data["jingle"]))

    async def radio(call: ServiceCall) -> None:
        if call.data.get("stop"):
            await _run(hass, call, lambda c, mac: c.radio(mac, stop=True))
            return
        station = call.data.get("station")
        if not station:
            raise ServiceValidationError("give it a station, or stop: true")
        await _run(hass, call, lambda c, mac: c.radio(mac, station))

    async def podcast(call: ServiceCall) -> None:
        await _run(
            hass,
            call,
            lambda c, mac: c.podcast(
                mac, call.data.get("feed"), call.data["episode"], call.data["stop"]
            ),
        )

    async def ears(call: ServiceCall) -> None:
        await _run(
            hass,
            call,
            lambda c, mac: c.ears(mac, call.data["left"], call.data["right"]),
        )

    async def mail(call: ServiceCall) -> None:
        await _run(
            hass,
            call,
            lambda c, mac: c.send_mail(
                mac, call.data["to"], call.data["text"], call.data.get("jingle")
            ),
        )

    for name, handler, schema in (
        (SERVICE_SPEAK, speak, SPEAK_SCHEMA),
        (SERVICE_NOTIFY, notify, NOTIFY_SCHEMA),
        (SERVICE_JINGLE, jingle, JINGLE_SCHEMA),
        (SERVICE_RADIO, radio, RADIO_SCHEMA),
        (SERVICE_PODCAST, podcast, PODCAST_SCHEMA),
        (SERVICE_EARS, ears, EARS_SCHEMA),
        (SERVICE_MAIL, mail, MAIL_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)
