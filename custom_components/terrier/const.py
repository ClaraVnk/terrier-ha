"""Constants for the Le Terrier integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "terrier"

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"

# The Terrier answers from memory for everything except the rabbit's own
# diagnostics, so polling is cheap. Thirty seconds is also the period of the
# warren's own scheduler, so a faster poll would only show the same numbers.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

MANUFACTURER = "Violet"
MODEL = "Nabaztag:tag v2"

# The belly palette the Terrier exposes, as RGB, so a light entity can show
# something honest in the colour wheel. These are the warren's own values.
COLOURS: dict[str, tuple[int, int, int]] = {
    "warm": (255, 150, 60),
    "amber": (255, 100, 20),
    "rose": (255, 90, 120),
    "violet": (140, 70, 200),
    "blue": (60, 120, 220),
    "green": (70, 180, 110),
    "white": (255, 220, 180),
}

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

# The belly palette as the warren names it. Distinct from COLOURS above,
# which maps those names to RGB for the light's colour wheel: these are the
# strings the API accepts, and the firmware knows no others.
BELLY_COLOURS = ("blue", "sky", "green", "red", "orange", "violet",
                 "yellow", "white")
