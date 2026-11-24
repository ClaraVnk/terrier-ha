"""Constants for the Le Terrier integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "terrier"

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"

# The listing (online, firmware, config) every thirty seconds — the period of
# the warren's own scheduler, so a faster poll would only show the same
# numbers. Everything else every five minutes. Review of 2026-11-18: each
# rabbit cost three more requests per cycle, one of them a 7-day event
# summary and one the waiting mail with every voice message in it as
# base64 — 200 KB per message, twice a minute, for a count.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
SLOW_INTERVAL = timedelta(minutes=5)

MANUFACTURER = "Violet"
MODEL = "Nabaztag:tag v2"

# The belly's palette, as the warren has it (indicators.BELLY_PALETTE): seven
# names, one bit per channel in the firmware, and no others. The RGB values
# are the warren's own (NIGHTLIGHT_COLOURS), so the light's colour wheel shows
# what the belly shows. Review of 2026-11-18: this table said warm, amber and
# rose — three names for the same red — and had no cyan and no yellow, so the
# light could not reach two of the seven and showed a stored "red" as warm.
COLOURS: dict[str, tuple[int, int, int]] = {
    "blue": (60, 120, 220),
    "green": (70, 180, 110),
    "cyan": (60, 200, 210),
    "red": (220, 70, 60),
    "violet": (140, 70, 200),
    "yellow": (240, 210, 70),
    "white": (255, 220, 180),
}
DEFAULT_COLOUR = "red"  # the warren's own default for the nightlight

# Names chosen before anybody had read the palette. A saved setting or an
# older automation may still say them; the warren reads them as these.
OLD_COLOURS: dict[str, str] = {
    "warm": "red",
    "amber": "red",
    "rose": "red",
    "orange": "red",
    "sky": "cyan",
}


def canon(colour: str | None) -> str | None:
    """A colour as the belly's palette calls it, or None if it has none."""
    name = OLD_COLOURS.get(colour or "", colour)
    return name if name in COLOURS else None


NOSE_MODES = ("off", "blink", "double")

SERVICE_NOTIFY = "notify"
SERVICE_SPEAK = "speak"
SERVICE_JINGLE = "jingle"
SERVICE_RADIO = "radio"
SERVICE_PODCAST = "podcast"
SERVICE_EARS = "ears"
SERVICE_MAIL = "mail"
# The rest of the warren, reachable at last — see settings.py for the
# settings that became entities instead.
SERVICE_ASK = "ask"
SERVICE_LISTEN = "listen"
SERVICE_AIR = "air"
SERVICE_AMBIENT = "ambient"
SERVICE_SET_CONFIG = "set_config"
SERVICE_RFID_BIND = "rfid_bind"
SERVICE_RFID_REMOVE = "rfid_remove"
SERVICE_TELL = "tell"
SERVICE_NOW = "now"
SERVICE_REMINDER_ADD = "reminder_add"
SERVICE_REMINDER_REMOVE = "reminder_remove"
SERVICE_BIRTHDAY_ADD = "birthday_add"
SERVICE_BIRTHDAY_REMOVE = "birthday_remove"
SERVICE_JOURNAL_ADD = "journal_add"
SERVICE_BUTTON_BIND = "button_bind"
SERVICE_BUTTON_REMOVE = "button_remove"
SERVICE_TRANSPORT_STOP = "transport_stop"

# What a tag or a head gesture can do, and what /tell can say -- the warren's lists.
ACTION_TYPES = (
    "say",
    "radio",
    "weather",
    "joke",
    "ephemeris",
    "transport",
    "story",
    "agenda",
    "listen",
    "pomodoro",
    "minuteur",
    "echo",
    "briefing",
    "home_summary",
    "fierte",
    "horoscope",
    "taichi",
    "rss",
    "webhook",
)
TELL = (
    "joke",
    "ephemeris",
    "transport",
    "story",
    "agenda",
    "alerts",
    "weather",
    "clock",
    "wakeup",
    "twitch",
    "pomodoro",
    "minuteur",
    "briefing",
    "home_summary",
    "fierte",
)
GESTURES = ("click", "double_click", "long_click", "double_long_click")

# The names the API accepts for the belly. One table, so the select, the
# light and the services cannot drift apart again (review of 2026-11-18).
BELLY_COLOURS = tuple(COLOURS)

# The page's "now" buttons, as the Terrier's /api/rabbits/<mac>/now takes them.
NOW = (
    "taichi",
    "story",
    "joke",
    "horoscope",
    "nameday",
    "briefing",
    "agenda",
    "news",
    "transport",
    "weather",
    "time",
    "compliment",
)
