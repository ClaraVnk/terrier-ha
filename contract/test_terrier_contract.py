"""The integration's own client against the real Terrier — no fake of either.

Le Terrier's code is private, so this cannot run in this repository's CI: it
is copied into a Terrier checkout's `tests/` and run there, with its
fixtures (`store`, `owner`, `app`, `xmpp`), `TERRIER_HA` pointing at this
checkout:

    cp contract/test_terrier_contract.py <terrier>/tests/
    cd <terrier> && TERRIER_HA=<terrier-ha> python -m pytest -q -o addopts= \\
        tests/test_terrier_contract.py

Each test states something the integration relies on. Written for the
review of 2026-11-18, which found the jingle, the ambient colour and the
nightlight palette each refused by the warren they were written for, and a
docstring promising a test like this that did not exist. It must pass on
the warren as it is and on one that has taken the server half of that
review.
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import pathlib
import re
import sys

import pytest
from tests.conftest import csrf_from
from yarl import URL

HA = pathlib.Path(os.environ.get("TERRIER_HA", "/src-ha"))
sys.path.insert(0, str(HA / "tests"))
import hastub  # noqa: E402,F401  (before custom_components)

from custom_components.terrier import api, const, coordinator  # noqa: E402

MAC = "0019dbdeadbe"
OTHER = "0019dbfeed11"


class _Resp:
    def __init__(self, r):
        self._r = r
        self.status = r.status_code
        self.reason = r.status
        self.content_type = r.mimetype

    async def json(self):
        return json.loads(self._r.get_data(as_text=True))


class _Ctx:
    def __init__(self, resp):
        self.resp = resp

    async def __aenter__(self):
        return self.resp

    async def __aexit__(self, *exc):
        return False


class FlaskSession:
    """aiohttp-shaped: each request goes to the Flask test client."""

    def __init__(self, client):
        self.client = client
        self.calls: list[tuple[str, str, int]] = []

    def request(self, method, url, json=None, timeout=None, headers=None):
        path = URL(str(url)).path_qs
        kw = {"headers": headers}
        if json is not None:
            kw["json"] = json
        r = self.client.open(path, method=method, **kw)
        self.calls.append((method, path, len(r.get_data())))
        return _Ctx(_Resp(r))


def run(coro):
    return asyncio.run(coro)


class Sess:
    def __init__(self):
        self.programs, self.packets, self.choreos = [], [], []

    def send_program(self, p):
        self.programs.append(p)

    def send_violet_packet(self, raw):
        self.packets.append(raw)

    def send_choreography(self, *a):
        self.choreos.append(a)

    def send_audio(self, url):
        pass


@pytest.fixture
def ha(store, owner, app, xmpp):
    store.touch_rabbit(MAC, ip="81.2.69.142")
    with store._cur() as cur:
        cur.execute(
            "UPDATE rabbits SET owner_id=(SELECT id FROM owners LIMIT 1), "
            "name='Nabi' WHERE mac=?",
            (MAC,),
        )
    tok = csrf_from(owner.get("/integration").get_data(as_text=True))
    owner.post("/integration/token", data={"_csrf": tok, "name": "Home Assistant"})
    html = owner.get("/integration").get_data(as_text=True)
    token = re.search(r"\btrr_[A-Za-z0-9_-]{20,}", html).group(0)
    sess = Sess()
    xmpp.online.append(MAC)
    xmpp.get_session = lambda m, **_kw: sess
    http = FlaskSession(app.test_client())
    return api.TerrierClient(http, "https://localhost/", token), sess, http


def _config(store):
    return store.get_rabbit(MAC)["config"] or {}


# --- actions ------------------------------------------------------------------
def test_jingle(ha, monkeypatch):
    from terrier import jingles

    monkeypatch.setattr(jingles, "list_jingles", lambda: ["bip"])
    client, sess, _ = ha
    run(client.play_jingle(MAC, "bip"))
    assert sess.programs


def test_ambient_colour_is_saved_as_the_breathing_colour(ha, store):
    client, _, _ = ha
    for colour in const.BELLY_COLOURS:
        run(client.breathe(MAC, colour))
        assert _config(store)["breath_colour"] == colour


def test_ambient_clear(ha):
    client, sess, _ = ha
    run(client.belly_clear(MAC))
    assert sess.packets


def test_tell_offers_what_the_warren_says(ha):
    client, _, _ = ha
    with pytest.raises(api.TerrierError) as e:
        run(client.tell(MAC, "__none__"))
    offered = str(e.value).split("what must be one of ", 1)[1].split(", ")
    assert set(offered) == set(const.TELL)


def test_every_action_type_can_be_bound(ha):
    client, _, _ = ha
    for kind in const.ACTION_TYPES:
        if kind in ("radio", "webhook"):  # a catalogued station; an address
            continue
        action = {"type": kind, "text": "coucou"} if kind == "say" else {"type": kind}
        run(client.button_bind(MAC, "click", action))
        run(client.rfid_bind(MAC, "d0021a0353a1b2c3", action))


# --- settings -----------------------------------------------------------------
def _table() -> dict[str, dict]:
    tree = ast.parse((HA / "custom_components/terrier/settings.py").read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and node.target.id in (
            "SWITCHES",
            "TIMES",
            "SELECTS",
            "NUMBERS",
        ):
            for call in node.value.elts:
                kw = {k.arg: k.value for k in call.keywords}
                out[ast.literal_eval(kw["key"])] = {
                    "options": ast.literal_eval(kw["options"])
                    if "options" in kw
                    else None
                }
    return out


def test_every_setting_entity_is_writable_with_the_same_options(ha):
    client, _, _ = ha
    writable = run(client._request("GET", f"/api/rabbits/{MAC}/settings"))["writable"]
    for key, row in _table().items():
        assert key in writable, key
        if row["options"] is not None:
            assert set(row["options"]) == set(writable[key]["values"]), key


def test_the_palette_is_the_warrens():
    from terrier import indicators

    assert set(const.COLOURS) == set(indicators.BELLY_PALETTE)
    for old in const.OLD_COLOURS:
        assert const.canon(old) == indicators.canon(old)


def test_the_light_reports_what_it_was_told(ha, store, monkeypatch):
    from terrier import indicators

    monkeypatch.setattr(indicators, "set_nightlight", lambda *a, **k: True)
    client, _, _ = ha
    run(client.nightlight(MAC, True, "cyan", 3))
    cfg = run(client.rabbit(MAC))["config"]
    assert (cfg["nightlight_colour"], cfg["nightlight_level"]) == ("cyan", 3)
    assert cfg["nightlight_on"] is True


# --- the poll ------------------------------------------------------------------
def _poll(c):
    c.data = run(c._async_update_data())
    return c.data


def test_a_v1_is_breathing(ha, store, xmpp):
    from terrier import nabv1

    xmpp.online.remove(MAC)  # a v1 has no XMPP session
    store.save_rabbit_config(MAC, {"hw": nabv1.HW})
    store.touch_rabbit(MAC)
    client, _, _ = ha
    assert _poll(coordinator.TerrierCoordinator(None, None, client))[MAC]["online"]


def test_the_poll_keeps_no_voice_message(ha, store):
    store.touch_rabbit(OTHER)
    store.post_mail(MAC, OTHER, "friend", "a private sentence", "", b"\xff" * 150_000)
    client, _, _ = ha
    data = _poll(coordinator.TerrierCoordinator(None, None, client))
    kept = json.dumps(data[MAC]["mail"])
    assert len(kept) < 1_000
    assert "a private sentence" not in kept
    assert data[MAC]["mail"]["waiting"][0]["from_handle"]


def test_a_poll_is_one_request_between_the_slow_ones(ha):
    client, _, http = ha
    c = coordinator.TerrierCoordinator(None, None, client)
    _poll(c)
    n = len(http.calls)
    _poll(c)
    assert [m for m, _p, _s in http.calls[n:]] == ["GET"]
    assert http.calls[-1][1] == "/api/rabbits"
