"""Setting it up: an address and a token, and nothing else to think about."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import TerrierAuthError, TerrierClient, TerrierError
from .const import (
    CONF_BASE_URL,
    CONF_BRAIN,
    CONF_BRAIN_AI,
    CONF_BRAIN_CAP,
    CONF_BRAIN_CONTEXT,
    CONF_BRAIN_WATCH,
    CONF_TOKEN,
    DEFAULT_BRAIN_CAP,
    DOMAIN,
)

DEFAULT_URL = "https://terrier.cyberloutre.fr"

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL, default=DEFAULT_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class TerrierConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask once, check it works, and say what is wrong when it does not."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return TerrierOptionsFlow()

    def __init__(self) -> None:
        self._reauth_entry_data: Mapping[str, Any] | None = None

    async def _check(self, base_url: str, token: str) -> tuple[str, dict[str, str]]:
        """(a title, errors). The token is verified before the entry exists —
        an integration that sets up cleanly and then fails forever is worse
        than one that refuses at the door."""
        if not base_url.lower().startswith("https://"):
            # The token travels in every request. Review of 2026-11-18: plain
            # http was accepted, and Le Terrier is only ever served over TLS.
            return "", {CONF_BASE_URL: "https_required"}
        client = TerrierClient(async_get_clientsession(self.hass), base_url, token)
        try:
            await client.rabbits()
        except TerrierAuthError:
            return "", {CONF_TOKEN: "invalid_auth"}
        except TerrierError:
            return "", {CONF_BASE_URL: "cannot_connect"}
        # An account with no rabbit yet is not refused any more (review of
        # 2026-11-18: it blocked set-up and re-auth alike, for an owner
        # between two rabbits). A rabbit adopted later appears on its own.
        host = base_url.split("//", 1)[-1].rstrip("/")
        return f"Le Terrier ({host})", {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].strip().rstrip("/")
            token = user_input[CONF_TOKEN].strip()
            await self.async_set_unique_id(base_url.lower())
            self._abort_if_unique_id_configured()
            title, errors = await self._check(base_url, token)
            if not errors:
                return self.async_create_entry(
                    title=title, data={CONF_BASE_URL: base_url, CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="user",
            data_schema=SCHEMA,
            errors=errors,
            # hassfest forbids URLs inside translated strings; they are
            # placeholders so the text stays translatable and the addresses
            # live in one place.
            description_placeholders={"hosted": DEFAULT_URL},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        self._reauth_entry_data = entry_data
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """A revoked token should ask for a new one, not break silently."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            base_url = entry.data[CONF_BASE_URL]
            token = user_input[CONF_TOKEN].strip()
            _title, errors = await self._check(base_url, token)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"url": entry.data[CONF_BASE_URL]},
        )


class TerrierOptionsFlow(OptionsFlow):
    """The rabbit's mind (brain.py): off by default. Which of Home
    Assistant's AI Task entities thinks, what it watches (what a person in
    the room would notice), what it is told about the home (the causes),
    and how many calls a day at most."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        opts = dict(self.config_entry.options)
        if user_input is not None:
            if user_input.get(CONF_BRAIN) and not user_input.get(CONF_BRAIN_AI):
                errors[CONF_BRAIN_AI] = "mind_needs_ai"
            elif user_input.get(CONF_BRAIN) and not user_input.get(CONF_BRAIN_WATCH):
                errors[CONF_BRAIN_WATCH] = "mind_needs_watch"
            else:
                return self.async_create_entry(data=user_input)
            opts = user_input
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BRAIN, default=bool(opts.get(CONF_BRAIN))
                ): BooleanSelector(),
                vol.Optional(
                    CONF_BRAIN_AI,
                    description={"suggested_value": opts.get(CONF_BRAIN_AI)},
                ): EntitySelector(EntitySelectorConfig(domain="ai_task")),
                vol.Optional(
                    CONF_BRAIN_WATCH, default=opts.get(CONF_BRAIN_WATCH) or []
                ): EntitySelector(EntitySelectorConfig(multiple=True)),
                vol.Optional(
                    CONF_BRAIN_CONTEXT, default=opts.get(CONF_BRAIN_CONTEXT) or []
                ): EntitySelector(EntitySelectorConfig(multiple=True)),
                vol.Required(
                    CONF_BRAIN_CAP,
                    default=int(opts.get(CONF_BRAIN_CAP) or DEFAULT_BRAIN_CAP),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=500, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
