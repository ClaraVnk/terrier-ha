"""A thin async client for a Terrier's HTTP API.

Deliberately thin: it knows how to authenticate, how to turn a failure into
one of three exceptions, and nothing else. Every bit of meaning about what a
rabbit *is* lives in the entities, where Home Assistant can see it.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
from yarl import URL

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=15)
# A question and a push-to-talk wait for the warren's speech-to-text (60 s),
# its model (45 s) and the synthesis, after up to 8 s of listening. Review of
# 2026-11-18: at 15 s the automation got "timed out" while the rabbit
# answered anyway, and a retry spent the owner's quota a second time.
LONG_TIMEOUT = aiohttp.ClientTimeout(total=150)

_MAC = re.compile(r"[0-9a-fA-F]{12}")
_NOTHING = object()


class TerrierError(Exception):
    """Any failure talking to a Terrier."""


class TerrierAuthError(TerrierError):
    """The token was refused. Home Assistant turns this into a re-auth flow."""


class TerrierOffline(TerrierError):
    """The warren answered, but the rabbit is not connected to it.

    Distinct from TerrierError on purpose: a rabbit that is merely unplugged
    is not a broken integration, and logging it as one trains people to ignore
    their logs.
    """


def _where(path: str) -> str:
    """The path, with the rabbit's MAC cut to its last four digits.

    These messages end up in Home Assistant's log and in bug reports pasted
    into public issues (review of 2026-11-18); four digits still tell two
    rabbits apart.
    """
    return _MAC.sub(lambda m: "…" + m.group(0)[-4:], path)


def _why(resp: aiohttp.ClientResponse, body: Any) -> str:
    """What the warren said, in the words it said it.

    A refused settings write answers `{"error": "nothing was changed",
    "errors": {"nightlight_colour": "expected one of ..."}}`. Reporting only
    the first half tells an owner that something failed and not which setting
    or why, which is the least useful half of a perfectly good answer.
    """
    body = body if isinstance(body, dict) else {}
    detail = body.get("errors")
    if isinstance(detail, dict) and detail:
        return "; ".join(f"{k}: {v}" for k, v in sorted(detail.items()))
    # Never the body of an answer that is not the warren's JSON. Review of
    # 2026-11-18: a proxy's 502 page went whole into the message — 20 KB of
    # HTML in Home Assistant's log on every poll.
    reason = getattr(resp, "reason", None) or ""
    return str(body.get("error") or f"HTTP {resp.status} {reason}".strip())


class TerrierClient:
    """Talks to one Terrier."""

    def __init__(
        self, session: aiohttp.ClientSession, base_url: str, token: str
    ) -> None:
        # Normalised once: a trailing slash in the config entry is the single
        # most common way a URL ends up with a double slash in every request.
        self._base = URL(base_url.rstrip("/") + "/")
        self._session = session
        self._token = token

    @property
    def base_url(self) -> str:
        return str(self._base).rstrip("/")

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        timeout: aiohttp.ClientTimeout = TIMEOUT,
    ) -> Any:
        url = self._base.join(URL(path.lstrip("/")))
        where = _where(path)
        try:
            async with self._session.request(
                method,
                url,
                json=json,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self._token}"},
            ) as resp:
                # 401 only. The warren answers 401 to a bad token and 404 to a
                # rabbit that is not yours; a 403 can only come from a proxy
                # or a firewall in between, and a new token would not get
                # past it (review of 2026-11-18).
                if resp.status == 401:
                    raise TerrierAuthError("the API token was refused")
                body: Any = _NOTHING
                if resp.content_type == "application/json":
                    try:
                        body = await resp.json()
                    except ValueError as err:
                        # Truncated, or a page labelled JSON. Review of
                        # 2026-11-18: this escaped as a raw JSONDecodeError,
                        # which nothing upstream catches.
                        raise TerrierError(f"{where}: not valid JSON") from err
                if resp.status == 503:
                    # The warren's own word for "the rabbit is not there".
                    said = body.get("error") if isinstance(body, dict) else None
                    raise TerrierOffline(str(said or "the rabbit is not connected"))
                if resp.status == 404:
                    raise TerrierError(f"{where}: not found")
                if resp.status >= 400:
                    raise TerrierError(f"{where}: {_why(resp, body)}")
                if body is _NOTHING:
                    # A 200 that is not JSON is a captive portal or a proxy's
                    # page, not an empty answer.
                    raise TerrierError(f"{where}: not a JSON answer")
                return body
        except TimeoutError as err:
            raise TerrierError(f"{where}: timed out") from err
        except aiohttp.ClientError as err:
            raise TerrierError(f"{where}: {err}") from err

    async def _dict(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        timeout: aiohttp.ClientTimeout = TIMEOUT,
    ) -> dict[str, Any]:
        """An answer that has to be an object, or a TerrierError."""
        body = await self._request(method, path, json, timeout)
        if not isinstance(body, dict):
            raise TerrierError(f"{_where(path)}: unexpected answer")
        return body

    # --- reading ---------------------------------------------------------
    async def rabbits(self) -> list[dict[str, Any]]:
        listing = await self._request("GET", "/api/rabbits")
        # Review of 2026-11-18: `{"error": "maintenance"}` with a 200 became
        # an AttributeError in the coordinator instead of a failed poll.
        if not isinstance(listing, list) or not all(
            isinstance(r, dict) for r in listing
        ):
            raise TerrierError("/api/rabbits: unexpected answer")
        return listing

    async def rabbit(self, mac: str) -> dict[str, Any]:
        return await self._dict("GET", f"/api/rabbits/{mac}")

    async def mood(self, mac: str) -> dict[str, Any]:
        return await self._dict("GET", f"/api/rabbits/{mac}/mood")

    async def mail(self, mac: str) -> dict[str, Any]:
        """Who is waiting, and nothing else.

        The warren's answer carried each voice message as base64 and each
        text in full (review of 2026-11-18); the sensor needs a count and the
        senders. Whatever the warren sends, only that is kept in memory.
        """
        body = await self._dict("GET", f"/api/rabbits/{mac}/mail")
        waiting = body.get("waiting")
        return {
            "handle": body.get("handle"),
            "waiting": [
                {
                    "id": m.get("id"),
                    "from_handle": m.get("from_handle"),
                    "created_at": m.get("created_at"),
                    "has_audio": bool(m.get("has_audio") or m.get("audio")),
                }
                for m in (waiting if isinstance(waiting, list) else [])
                if isinstance(m, dict)
            ],
        }

    # --- doing -----------------------------------------------------------
    async def notify(self, mac: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Belly, nose, counter, jingle and words in one call."""
        body = {k: v for k, v in fields.items() if v not in (None, "")}
        return await self._request("POST", f"/api/rabbits/{mac}/notify", body)

    async def speak(self, mac: str, text: str) -> None:
        await self._request("POST", f"/api/rabbits/{mac}/speak", {"text": text})

    async def play_jingle(self, mac: str, name: str) -> None:
        # `name`, as the warren reads it. Review of 2026-11-18: this sent
        # `jingle`, and every call since the service existed was refused.
        await self._request("POST", f"/api/rabbits/{mac}/jingle", {"name": name})

    async def radio(
        self, mac: str, station: str | None = None, stop: bool = False
    ) -> None:
        body = {"stop": True} if stop else {"station": station}
        await self._request("POST", f"/api/rabbits/{mac}/radio", body)

    async def podcast(
        self, mac: str, feed: str | None = None, episode: int = 0, stop: bool = False
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"stop": True} if stop else {"episode": episode}
        if feed and not stop:
            body["feed"] = feed
        return await self._request("POST", f"/api/rabbits/{mac}/podcast", body)

    async def ears(self, mac: str, left: int, right: int) -> None:
        await self._request(
            "POST", f"/api/rabbits/{mac}/ears", {"left": left, "right": right}
        )

    async def sleep(self, mac: str, asleep: bool) -> None:
        await self._request("POST", f"/api/rabbits/{mac}/sleep", {"asleep": asleep})

    async def nose(self, mac: str, mode: str) -> None:
        await self._request("POST", f"/api/rabbits/{mac}/nose", {"mode": mode})

    async def counter(self, mac: str, value: int, label: str | None = None) -> None:
        body: dict[str, Any] = {"value": value}
        if label is not None:
            body["label"] = label
        await self._request("POST", f"/api/rabbits/{mac}/counter", body)

    async def nightlight(
        self, mac: str, on: bool, colour: str | None = None, level: int | None = None
    ) -> None:
        body: dict[str, Any] = {"on": on}
        if colour:
            body["colour"] = colour
        if level is not None:
            body["level"] = level
        await self._request("POST", f"/api/rabbits/{mac}/nightlight", body)
        if on and (colour or level is not None):
            # Saved as the nightlight's colour and level too. Review of
            # 2026-11-18: the warren lit the colour but kept the old one in
            # the config, so the light reported the old colour and the
            # scheduler put it back on its next tick. Harmless on a warren
            # that saves them itself.
            patch: dict[str, Any] = {}
            if colour:
                patch["nightlight_colour"] = colour
            if level is not None:
                patch["nightlight_level"] = level
            await self.set_config(mac, patch)

    async def compliment(self, mac: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/rabbits/{mac}/compliment")

    async def send_mail(
        self, mac: str, to: str, text: str, jingle: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"to": to, "text": text}
        if jingle:
            body["jingle"] = jingle
        return await self._request("POST", f"/api/rabbits/{mac}/mail", body)

    # -- the rest of the warren ------------------------------------------- #

    async def say_air(self, mac: str) -> dict[str, Any]:
        """Say the air quality now, rather than waiting for the daily hour."""
        return await self._request("POST", f"/api/rabbits/{mac}/air", {})

    async def breathe(self, mac: str, colour: str) -> dict[str, Any]:
        """The colour the belly breathes in: the `breath_colour` setting.

        Review of 2026-11-18: this posted `{"colour": ...}` to `/ambient`, a
        raw diagnostic that wants a service number and a byte, and every call
        was refused. The warren applies the setting on its next tick.
        """
        return await self.set_config(mac, {"breath_colour": colour})

    async def belly_clear(self, mac: str) -> dict[str, Any]:
        """Stop every ambient service and put the bottom LED out."""
        return await self._request("POST", f"/api/rabbits/{mac}/belly/clear", {})

    async def ask(self, mac: str, question: str) -> dict[str, Any]:
        return await self._dict(
            "POST", f"/api/rabbits/{mac}/ask", {"q": question}, LONG_TIMEOUT
        )

    async def listen(self, mac: str, seconds: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if seconds:
            body["seconds"] = seconds
        return await self._dict(
            "POST", f"/api/rabbits/{mac}/listen", body, LONG_TIMEOUT
        )

    async def set_config(self, mac: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Write settings. The warren applies all of them or none, so a
        caller that gets a 200 knows exactly where it stands.

        A dict, not keyword arguments: review of 2026-11-18, a setting named
        `mac` sent through `terrier.set_config` crashed with a TypeError.
        """
        return await self._request("POST", f"/api/rabbits/{mac}/config", patch)

    async def rfid_bind(
        self, mac: str, tag: str, action: dict[str, Any]
    ) -> dict[str, Any]:
        body = {**action, "tag": tag}
        return await self._request("POST", f"/api/rabbits/{mac}/rfid", body)

    async def rfid_remove(self, mac: str, tag: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/rabbits/{mac}/rfid/{tag}")

    async def tell(self, mac: str, what: str) -> dict[str, Any]:
        """One of the rabbit's services, now: a joke, the name day, the next
        departures, a story, the agenda, the alerts, the weather..."""
        return await self._request("POST", f"/api/rabbits/{mac}/tell", {"what": what})

    async def volume(self, mac: str, percent: int) -> dict[str, Any]:
        """The loudness, 0-100: saved and sent to the rabbit now; a radio
        playing starts again at the new volume (Terrier 2026-11-24)."""
        return await self._request(
            "POST", f"/api/rabbits/{mac}/volume", {"percent": percent}
        )

    async def now(self, mac: str, what: str) -> dict[str, Any]:
        """One of the page's "now" actions: taichi, story, joke, horoscope,
        nameday, briefing, agenda, news, transport, weather, time, compliment."""
        return await self._request("POST", f"/api/rabbits/{mac}/now", {"what": what})

    async def reminder_add(self, mac: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", f"/api/rabbits/{mac}/reminders", fields)

    async def reminder_remove(self, mac: str, rid: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/rabbits/{mac}/reminders/{rid}")

    async def birthday_add(self, mac: str, name: str, day: str) -> dict[str, Any]:
        body = {"name": name, "day": day}
        return await self._request("POST", f"/api/rabbits/{mac}/birthdays", body)

    async def journal_add(self, mac: str, text: str) -> dict[str, Any]:
        body = {"text": text}
        return await self._request("POST", f"/api/rabbits/{mac}/journal", body)

    async def birthday_remove(self, mac: str, bid: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/rabbits/{mac}/birthdays/{bid}")

    async def button_bind(
        self, mac: str, gesture: str, action: dict[str, Any]
    ) -> dict[str, Any]:
        body = {**action, "gesture": gesture}
        return await self._request("POST", f"/api/rabbits/{mac}/button", body)

    async def button_remove(self, mac: str, gesture: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/rabbits/{mac}/button/{gesture}")

    async def transport_stop(
        self, mac: str, network: str, sid: str, name: str
    ) -> dict[str, Any]:
        body = {"network": network, "id": sid, "name": name}
        return await self._request("POST", f"/api/rabbits/{mac}/transport/stop", body)
