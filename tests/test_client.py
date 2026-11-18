"""The client against a warren that misbehaves, over real HTTP.

A local aiohttp server plays the Terrier: what it answers is chosen per test,
and what the client sent is recorded. Each test is a finding of the review of
2026-11-18 and failed on the code it was written against.
"""

from __future__ import annotations

import asyncio
from typing import Any

import hastub  # noqa: F401  (before custom_components)
import pytest
from aiohttp import ClientSession, web

from custom_components.terrier import api

MAC = "0019dbdeadbe"
TOKEN = "trr_" + "x" * 30


def run(coro):
    return asyncio.run(coro)


async def _with(routes: list, body) -> list[dict[str, Any]]:
    """Serve `routes`, run `body(client)`, return what the client sent."""
    seen: list[dict[str, Any]] = []

    @web.middleware
    async def record(request, handler):
        seen.append(
            {
                "method": request.method,
                "path": request.path,
                "json": await request.json() if request.can_read_body else None,
            }
        )
        return await handler(request)

    app = web.Application(middlewares=[record])
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with ClientSession() as session:
            await body(api.TerrierClient(session, f"http://127.0.0.1:{port}", TOKEN))
    finally:
        await runner.cleanup()
    return seen


async def _ok(_request):
    return web.json_response({"ok": True})


# --- H1 ---------------------------------------------------------------------
def test_a_jingle_is_asked_for_by_name():
    """The warren reads `name` (terrier ui.py api_jingle); this sent `jingle`."""

    async def body(c):
        await c.play_jingle(MAC, "bip")

    seen = run(_with([web.post(f"/api/rabbits/{MAC}/jingle", _ok)], body))
    assert seen[0]["json"] == {"name": "bip"}


# --- M4 ---------------------------------------------------------------------
def test_malformed_json_is_a_terrier_error():
    async def broken(_):
        return web.Response(text='[{"mac": ', content_type="application/json")

    async def body(c):
        with pytest.raises(api.TerrierError):
            await c.rabbits()

    run(_with([web.get("/api/rabbits", broken)], body))


def test_a_listing_that_is_not_a_list_is_a_terrier_error():
    async def wrong(_):
        return web.json_response({"error": "maintenance"})

    async def body(c):
        with pytest.raises(api.TerrierError):
            await c.rabbits()

    run(_with([web.get("/api/rabbits", wrong)], body))


def test_a_detail_that_is_not_an_object_is_a_terrier_error():
    async def wrong(_):
        return web.json_response(["not", "a", "rabbit"])

    async def body(c):
        with pytest.raises(api.TerrierError):
            await c.rabbit(MAC)

    run(_with([web.get(f"/api/rabbits/{MAC}", wrong)], body))


def test_a_page_with_a_200_is_not_an_empty_listing():
    """A captive portal answers 200 with HTML; that is not "no rabbits"."""

    async def portal(_):
        return web.Response(text="<html>log in</html>", content_type="text/html")

    async def body(c):
        with pytest.raises(api.TerrierError):
            await c.rabbits()

    run(_with([web.get("/api/rabbits", portal)], body))


# --- L2 ---------------------------------------------------------------------
def test_an_html_error_page_is_not_pasted_into_the_message():
    async def gateway(_):
        return web.Response(
            status=502,
            text="<html>" + "x" * 20_000 + "</html>",
            content_type="text/html",
        )

    async def body(c):
        with pytest.raises(api.TerrierError) as e:
            await c.rabbits()
        assert len(str(e.value)) < 200, f"{len(str(e.value))} chars"
        assert "502" in str(e.value)
        assert "<html>" not in str(e.value)

    run(_with([web.get("/api/rabbits", gateway)], body))


def test_the_warrens_own_reasons_are_still_given():
    async def refused(_):
        return web.json_response(
            {"error": "nothing was changed", "errors": {"x": "not writable"}},
            status=400,
        )

    async def body(c):
        with pytest.raises(api.TerrierError, match="x: not writable"):
            await c.set_config(MAC, {"x": 1})

    run(_with([web.post(f"/api/rabbits/{MAC}/config", refused)], body))


# --- L1 ---------------------------------------------------------------------
def test_a_setting_called_mac_is_sent_like_any_other():
    """`terrier.set_config` accepts any string key; `mac` crashed the call."""

    async def body(c):
        await c.set_config(MAC, {"mac": "0019db000000", "self": 1})

    seen = run(_with([web.post(f"/api/rabbits/{MAC}/config", _ok)], body))
    assert seen[0]["json"] == {"mac": "0019db000000", "self": 1}


# --- L5 ---------------------------------------------------------------------
def test_only_a_401_asks_for_a_new_token():
    async def forbidden(_):
        return web.Response(status=403, text="blocked by the firewall")

    async def unauthorised(_):
        return web.json_response({"error": "unauthorised"}, status=401)

    async def body(c):
        with pytest.raises(api.TerrierError) as e:
            await c.rabbits()
        assert not isinstance(e.value, api.TerrierAuthError)
        with pytest.raises(api.TerrierAuthError):
            await c.rabbit(MAC)

    run(
        _with(
            [
                web.get("/api/rabbits", forbidden),
                web.get(f"/api/rabbits/{MAC}", unauthorised),
            ],
            body,
        )
    )


# --- L3 ---------------------------------------------------------------------
def test_an_error_does_not_carry_the_whole_mac():
    async def gone(_):
        return web.json_response({"error": "no such rabbit"}, status=404)

    async def body(c):
        with pytest.raises(api.TerrierError) as e:
            await c.rabbit(MAC)
        assert MAC not in str(e.value)
        assert MAC[-4:] in str(e.value)

    run(_with([web.get(f"/api/rabbits/{MAC}", gone)], body))


# --- H3 ---------------------------------------------------------------------
def test_the_waiting_mail_keeps_no_voice_and_no_text():
    """The warren sends each voice message as base64 (~200 KB) and each
    text; the sensor needs the senders. Neither stays in memory."""

    async def mail(_):
        return web.json_response(
            {
                "handle": "nabi",
                "waiting": [
                    {
                        "id": 7,
                        "from_handle": "friend",
                        "body": "a private sentence",
                        "jingle": "",
                        "audio": "A" * 200_000,
                        "created_at": "2026-11-18T10:00:00Z",
                    }
                ],
            }
        )

    async def body(c):
        got = await c.mail(MAC)
        assert got["handle"] == "nabi"
        assert got["waiting"] == [
            {
                "id": 7,
                "from_handle": "friend",
                "created_at": "2026-11-18T10:00:00Z",
                "has_audio": True,
            }
        ]

    run(_with([web.get(f"/api/rabbits/{MAC}/mail", mail)], body))


def test_the_waiting_mail_reads_a_warren_that_sends_no_audio():
    """The shape the warren is moving to: `has_audio`, no `audio`."""

    async def mail(_):
        return web.json_response(
            {
                "handle": "nabi",
                "waiting": [{"id": 1, "from_handle": "f", "has_audio": True}],
            }
        )

    async def body(c):
        got = await c.mail(MAC)
        assert got["waiting"][0]["has_audio"] is True

    run(_with([web.get(f"/api/rabbits/{MAC}/mail", mail)], body))


# --- M1 (the light's half) --------------------------------------------------
def test_turning_the_light_on_saves_its_colour_and_level():
    """The warren lit the colour and kept the old one in its config, so the
    light reported the old one and the scheduler put it back."""

    async def body(c):
        await c.nightlight(MAC, True, "blue", 3)

    seen = run(
        _with(
            [
                web.post(f"/api/rabbits/{MAC}/nightlight", _ok),
                web.post(f"/api/rabbits/{MAC}/config", _ok),
            ],
            body,
        )
    )
    assert [s["path"].rsplit("/", 1)[-1] for s in seen] == ["nightlight", "config"]
    assert seen[1]["json"] == {"nightlight_colour": "blue", "nightlight_level": 3}


def test_turning_the_light_off_writes_nothing_else():
    async def body(c):
        await c.nightlight(MAC, False)

    seen = run(_with([web.post(f"/api/rabbits/{MAC}/nightlight", _ok)], body))
    assert len(seen) == 1


# --- M6 ---------------------------------------------------------------------
class _Recording:
    """An aiohttp-shaped session that answers {} and keeps the kwargs."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, method, url, **kw):
        self.calls.append({"method": method, "url": str(url), **kw})
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    status = 200
    content_type = "application/json"

    async def json(self):
        return {}


def test_a_question_waits_for_the_answer():
    """The warren may need 8 s + 60 s (speech-to-text) + 45 s (model) + TTS."""
    session = _Recording()
    client = api.TerrierClient(session, "https://terrier.example.com", TOKEN)
    run(client.ask(MAC, "quel temps ?"))
    run(client.listen(MAC, 5))
    run(client.speak(MAC, "bonjour"))
    ask, listen, speak = (c["timeout"].total for c in session.calls)
    assert ask >= 120
    assert listen >= 120
    assert speak == 15
