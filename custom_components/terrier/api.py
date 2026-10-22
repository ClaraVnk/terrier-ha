"""A thin async client for a Terrier's HTTP API.

Deliberately thin: it knows how to authenticate, how to turn a failure into
one of three exceptions, and nothing else. Every bit of meaning about what a
rabbit *is* lives in the entities, where Home Assistant can see it.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from yarl import URL

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=15)


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


async def _why(resp: aiohttp.ClientResponse, body: Any) -> str:
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
    return str(body.get("error") or f"HTTP {resp.status} {await resp.text()}")


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
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> Any:
        url = self._base.join(URL(path.lstrip("/")))
        try:
            async with self._session.request(
                method,
                url,
                json=json,
                timeout=TIMEOUT,
                headers={"Authorization": f"Bearer {self._token}"},
            ) as resp:
                if resp.status in (401, 403):
                    raise TerrierAuthError("the API token was refused")
                body: Any = None
                if resp.content_type == "application/json":
                    body = await resp.json()
                if resp.status == 503:
                    # The warren's own word for "the rabbit is not there".
                    raise TerrierOffline(
                        (body or {}).get("error", "the rabbit is not connected")
                    )
                if resp.status == 404:
                    raise TerrierError(f"{path}: not found")
                if resp.status >= 400:
                    raise TerrierError(f"{path}: {await _why(resp, body)}")
                return body
        except TimeoutError as err:
            raise TerrierError(f"{path}: timed out") from err
        except aiohttp.ClientError as err:
            raise TerrierError(f"{path}: {err}") from err

    # --- reading ---------------------------------------------------------
    async def rabbits(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/rabbits") or []

    async def rabbit(self, mac: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/rabbits/{mac}") or {}

    async def mood(self, mac: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/rabbits/{mac}/mood") or {}

    async def mail(self, mac: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/rabbits/{mac}/mail") or {}

    async def jingles(self) -> list[str]:
        return await self._request("GET", "/api/jingles") or []

    # --- doing -----------------------------------------------------------
    async def notify(self, mac: str, **fields: Any) -> dict[str, Any]:
        """Belly, nose, counter, jingle and words in one call."""
        body = {k: v for k, v in fields.items() if v not in (None, "")}
        return await self._request("POST", f"/api/rabbits/{mac}/notify", body)

    async def speak(self, mac: str, text: str) -> None:
        await self._request("POST", f"/api/rabbits/{mac}/speak", {"text": text})

    async def play_jingle(self, mac: str, name: str) -> None:
        await self._request("POST", f"/api/rabbits/{mac}/jingle", {"jingle": name})

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

    async def compliment(self, mac: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/rabbits/{mac}/compliment")

    async def send_mail(
        self, mac: str, to: str, text: str, jingle: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"to": to, "text": text}
        if jingle:
            body["jingle"] = jingle
        return await self._request("POST", f"/api/rabbits/{mac}/mail", body)

    async def nudge_mood(self, mac: str, kind: str = "speak") -> dict[str, Any]:
        return await self._request("POST", f"/api/rabbits/{mac}/mood", {"kind": kind})

    # -- the rest of the warren ------------------------------------------- #
    # Everything below exists because the integration covered sixteen of the
    # Terrier's routes and the warren has thirty-one. Some of the gap was
    # ours; some of it was a route that did not exist yet.

    async def state(self, mac: str) -> dict[str, Any]:
        """What the belly and the ears are actually doing, read back from the
        rabbit rather than inferred from what we last told it."""
        return await self._request("GET", f"/api/rabbits/{mac}/state") or {}

    async def air(self, mac: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/rabbits/{mac}/air") or {}

    async def say_air(self, mac: str) -> dict[str, Any]:
        """Say the air quality now, rather than waiting for the daily hour."""
        return await self._request("POST", f"/api/rabbits/{mac}/air", {}) or {}

    async def alarm(self, mac: str, **fields: Any) -> dict[str, Any]:
        return await self._request("POST", f"/api/rabbits/{mac}/alarm", fields) or {}

    async def ambient(self, mac: str, **fields: Any) -> dict[str, Any]:
        """The colour the belly breathes in. Clearing it stops the breathing,
        which is not obvious and is why `clear` is explicit."""
        return await self._request("POST", f"/api/rabbits/{mac}/ambient", fields) or {}

    async def ask(self, mac: str, question: str) -> dict[str, Any]:
        return (
            await self._request("POST", f"/api/rabbits/{mac}/ask", {"q": question})
            or {}
        )

    async def listen(self, mac: str, seconds: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if seconds:
            body["seconds"] = seconds
        return await self._request("POST", f"/api/rabbits/{mac}/listen", body) or {}

    async def settings(self, mac: str) -> dict[str, Any]:
        """What this warren will accept — so a client need not hard-code
        eight belly colours."""
        return await self._request("GET", f"/api/rabbits/{mac}/settings") or {}

    async def set_config(self, mac: str, **patch: Any) -> dict[str, Any]:
        """Write settings. The warren applies all of them or none, so a
        caller that gets a 200 knows exactly where it stands."""
        return await self._request("POST", f"/api/rabbits/{mac}/config", patch) or {}

    async def rfid_bind(self, mac: str, tag: str, **action: Any) -> dict[str, Any]:
        body = {"tag": tag, **action}
        return await self._request("POST", f"/api/rabbits/{mac}/rfid", body) or {}

    async def rfid_remove(self, mac: str, tag: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/rabbits/{mac}/rfid/{tag}") or {}
