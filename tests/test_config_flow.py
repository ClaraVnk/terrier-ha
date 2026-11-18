"""Setting up: what the form refuses and what it lets through.

Review of 2026-11-18 (L4, L7).
"""

from __future__ import annotations

import asyncio

import hastub  # noqa: F401  (before custom_components)
import pytest

from custom_components.terrier import config_flow


class Session:
    def __init__(self, listing):
        self.listing = listing
        self.urls: list[str] = []

    def request(self, method, url, **_kw):
        self.urls.append(str(url))
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    status = 200
    content_type = "application/json"

    async def json(self):
        return self.listing


@pytest.fixture
def check(monkeypatch):
    def _check(url, listing):
        session = Session(listing)
        monkeypatch.setattr(config_flow, "async_get_clientsession", lambda _h: session)
        flow = config_flow.TerrierConfigFlow()
        flow.hass = None
        return asyncio.run(flow._check(url, "trr_x")), session

    return _check


def test_a_plain_http_address_is_refused_before_the_token_is_sent(check):
    (_title, errors), session = check("http://terrier.example.com", [])
    assert errors == {"base_url": "https_required"}
    assert session.urls == [], "the token never left"


def test_an_account_with_no_rabbit_yet_can_be_set_up(check):
    (title, errors), _ = check("https://terrier.example.com", [])
    assert errors == {}
    assert title == "Le Terrier (terrier.example.com)"
