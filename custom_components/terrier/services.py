"""The verbs: everything a rabbit does that is not a state to be toggled.

Targeted at devices rather than entities. "Speak" is not a property of the
belly light or the counter — it is something the rabbit does — and hanging it
off an arbitrary entity would make every automation read as though it were.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import TerrierError, TerrierOffline
from .const import (
    BELLY_COLOURS,
    COLOURS,
    DOMAIN,
    NOSE_MODES,
    SERVICE_AIR,
    SERVICE_AMBIENT,
    SERVICE_ASK,
    SERVICE_EARS,
    SERVICE_JINGLE,
    SERVICE_LISTEN,
    SERVICE_MAIL,
    SERVICE_NOTIFY,
    SERVICE_PODCAST,
    SERVICE_RADIO,
    SERVICE_RFID_BIND,
    SERVICE_RFID_REMOVE,
    SERVICE_SET_CONFIG,
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
ASK_SCHEMA = vol.Schema({**_TARGET, vol.Required("question"): cv.string})
LISTEN_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Optional("seconds"): vol.All(vol.Coerce(float), vol.Range(min=1, max=8)),
    }
)
AIR_SCHEMA = vol.Schema({**_TARGET})
AMBIENT_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Exclusive("colour", "what"): vol.In(BELLY_COLOURS),
        vol.Exclusive("clear", "what"): cv.boolean,
    }
)
SET_CONFIG_SCHEMA = vol.Schema(
    {**_TARGET, vol.Required("settings"): vol.Schema({cv.string: object})}
)
RFID_BIND_SCHEMA = vol.Schema(
    {
        **_TARGET,
        vol.Required("tag"): cv.string,
        vol.Required("type"): vol.In(("say", "radio", "weather", "webhook")),
        vol.Optional("text"): cv.string,
        vol.Optional("station"): cv.string,
        vol.Optional("url"): cv.url,
    }
)
RFID_REMOVE_SCHEMA = vol.Schema({**_TARGET, vol.Required("tag"): cv.string})
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


async def _ask_one(hass: HomeAssistant, call: ServiceCall, verb) -> ServiceResponse:
    """Like `_run`, but hands back what the rabbit heard and said.

    A question with no answer would be a strange thing to automate, so these
    two return a response. Several targets answer as a dict keyed by MAC
    rather than the last one winning silently.
    """
    out: dict[str, Any] = {}
    for coordinator, mac in _targets(hass, call):
        try:
            out[mac] = await verb(coordinator.client, mac)
        except TerrierOffline as err:
            raise HomeAssistantError(f"the rabbit is not connected ({err})") from err
        except TerrierError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()
    return out


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

    async def ask(call: ServiceCall) -> ServiceResponse:
        return await _ask_one(
            hass, call, lambda c, mac: c.ask(mac, call.data["question"])
        )

    async def listen(call: ServiceCall) -> ServiceResponse:
        """Push-to-talk. The rabbit records one sentence, the warren
        transcribes it with the owner's key and the rabbit answers out
        loud — and the words come back here so an automation can act on
        them rather than only overhear them."""
        return await _ask_one(
            hass, call, lambda c, mac: c.listen(mac, call.data.get("seconds"))
        )

    async def air(call: ServiceCall) -> None:
        await _run(hass, call, lambda c, mac: c.say_air(mac))

    async def ambient(call: ServiceCall) -> None:
        """The colour the belly BREATHES in, which is not the same thing as
        lighting it: clearing the service stops the breathing altogether,
        which surprised the warren's own operator once already."""
        if call.data.get("clear"):
            fields: dict[str, Any] = {"clear": True}
        elif "colour" in call.data:
            fields = {"colour": call.data["colour"]}
        else:
            raise ServiceValidationError("give it a colour, or clear: true")
        await _run(hass, call, lambda c, mac: c.ambient(mac, **fields))

    async def set_config(call: ServiceCall) -> None:
        """The long tail: a wake word, a feed, coordinates, a model name.

        The warren applies the whole patch or none of it, so a failure here
        means nothing changed — there is no half-written rabbit to repair.
        API keys are refused on purpose: Home Assistant would have to hold
        one to send it.
        """
        settings = call.data["settings"]
        if not settings:
            raise ServiceValidationError("no settings given")
        await _run(hass, call, lambda c, mac: c.set_config(mac, **settings))

    async def rfid_bind(call: ServiceCall) -> None:
        action = {
            k: v for k, v in call.data.items() if k not in (ATTR_DEVICE_ID, "tag")
        }
        await _run(
            hass, call, lambda c, mac: c.rfid_bind(mac, call.data["tag"], **action)
        )

    async def rfid_remove(call: ServiceCall) -> None:
        await _run(hass, call, lambda c, mac: c.rfid_remove(mac, call.data["tag"]))

    for name, handler, schema in (
        (SERVICE_AIR, air, AIR_SCHEMA),
        (SERVICE_AMBIENT, ambient, AMBIENT_SCHEMA),
        (SERVICE_SET_CONFIG, set_config, SET_CONFIG_SCHEMA),
        (SERVICE_RFID_BIND, rfid_bind, RFID_BIND_SCHEMA),
        (SERVICE_RFID_REMOVE, rfid_remove, RFID_REMOVE_SCHEMA),
        (SERVICE_SPEAK, speak, SPEAK_SCHEMA),
        (SERVICE_NOTIFY, notify, NOTIFY_SCHEMA),
        (SERVICE_JINGLE, jingle, JINGLE_SCHEMA),
        (SERVICE_RADIO, radio, RADIO_SCHEMA),
        (SERVICE_PODCAST, podcast, PODCAST_SCHEMA),
        (SERVICE_EARS, ears, EARS_SCHEMA),
        (SERVICE_MAIL, mail, MAIL_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schema)

    # The two that answer. Registered apart because they carry a response,
    # and a service that returns one has to say so at registration time.
    for name, handler, schema in (
        (SERVICE_ASK, ask, ASK_SCHEMA),
        (SERVICE_LISTEN, listen, LISTEN_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN,
            name,
            handler,
            schema=schema,
            supports_response=SupportsResponse.ONLY,
        )
