"""Every rabbit setting, as Home Assistant entities, declared once.

The integration used to drive a rabbit and configure none of it: it called
sixteen of the warren's routes, and the ones it skipped were the daily
things — the morning weather, the alarm, the chime — plus everything that
lives on the settings page. An automation could make a rabbit talk and not
make it wake you up.

These are the settings worth a dashboard tile. Each row says which config
key it is, and the platform file builds the entity from it; the long tail
(a wake word, a feed URL, coordinates, a model name) goes through the
`terrier.set_config` service, which takes any of the fifty-eight keys the
warren declares in `/api/rabbits/<mac>/settings`.

`enabled` says whether the entity appears without being asked for. The ones
set False are real and work; they are the second knob of a pair, and
shipping thirty-seven entities per rabbit all switched on would bury the
five people actually use.

The API keys are not here and cannot be: the warren refuses to write them
over HTTP, because Home Assistant would have to hold one to send it, and a
key pasted into an automation is a key in a YAML backup.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityCategory


@dataclass(frozen=True, kw_only=True)
class Setting:
    """One config key, and how it should look."""

    key: str  # the warren's config key, and our entity key
    icon: str
    enabled: bool = True
    category: EntityCategory | None = EntityCategory.CONFIG
    options: tuple[str, ...] = ()  # selects only
    minimum: int = 0  # numbers only
    maximum: int = 100
    step: int = 1
    unit: str | None = None


# --------------------------------------------------------------- switches

SWITCHES: tuple[Setting, ...] = (
    Setting(key="weather_enabled", icon="mdi:weather-partly-cloudy"),
    Setting(key="air_enabled", icon="mdi:air-filter"),
    Setting(key="alarm_enabled", icon="mdi:alarm"),
    Setting(key="clock_enabled", icon="mdi:clock-outline"),
    Setting(key="night_enabled", icon="mdi:weather-night"),
    Setting(key="nightlight_enabled", icon="mdi:lightbulb-night"),
    Setting(key="podcast_enabled", icon="mdi:podcast"),
    Setting(key="tamagotchi_enabled", icon="mdi:emoticon-outline"),
    Setting(key="compliment_enabled", icon="mdi:heart-outline"),
    Setting(key="llm_enabled", icon="mdi:robot-outline"),
    # The second knob of a pair, or a thing you set once and forget.
    Setting(key="weather_rainbow", icon="mdi:looks", enabled=False),
    Setting(key="air_speak", icon="mdi:bullhorn-outline", enabled=False),
    Setting(key="alarm_weather", icon="mdi:weather-sunny-alert", enabled=False),
    Setting(key="hw_sleep", icon="mdi:power-sleep", enabled=False),
    Setting(key="surprise_enabled", icon="mdi:party-popper", enabled=False),
    Setting(key="presence_share", icon="mdi:account-group-outline", enabled=False),
    Setting(
        key="devmode",
        icon="mdi:bug-outline",
        enabled=False,
        category=EntityCategory.DIAGNOSTIC,
    ),
)

# ------------------------------------------------------------------ times

TIMES: tuple[Setting, ...] = (
    Setting(key="weather_hour", icon="mdi:weather-partly-cloudy"),
    Setting(key="alarm_hour", icon="mdi:alarm"),
    Setting(key="air_hour", icon="mdi:air-filter", enabled=False),
    Setting(key="compliment_hour", icon="mdi:heart-outline", enabled=False),
    Setting(key="podcast_hour", icon="mdi:podcast", enabled=False),
    Setting(key="clock_from", icon="mdi:clock-start", enabled=False),
    Setting(key="clock_to", icon="mdi:clock-end", enabled=False),
    Setting(key="night_from", icon="mdi:weather-night", enabled=False),
    Setting(key="night_to", icon="mdi:weather-sunset-up", enabled=False),
    Setting(key="nightlight_from", icon="mdi:lightbulb-night", enabled=False),
    Setting(key="nightlight_to", icon="mdi:lightbulb-night-outline", enabled=False),
)

# ---------------------------------------------------------------- selects

# The values are the warren's own. `/api/rabbits/<mac>/settings` lists them
# too, but an entity's options have to exist before the first poll answers,
# so they are mirrored here and guarded by a test that compares the two.
SELECTS: tuple[Setting, ...] = (
    Setting(
        key="personality",
        icon="mdi:drama-masks",
        options=("off", "discret", "normal", "vif"),
    ),
    Setting(
        key="voice_speed", icon="mdi:speedometer", options=("slow", "normal", "fast")
    ),
    Setting(key="night_mode", icon="mdi:weather-night", options=("quiet", "sleep")),
    Setting(
        key="nightlight_colour",
        icon="mdi:palette",
        options=("blue", "sky", "green", "red", "orange", "violet", "yellow", "white"),
    ),
    Setting(
        key="clock_mode",
        icon="mdi:bell-outline",
        enabled=False,
        options=("speak", "chime", "both"),
    ),
    Setting(
        key="clock_every",
        icon="mdi:timer-outline",
        enabled=False,
        options=("hour", "half"),
    ),
    Setting(
        key="weather_show",
        icon="mdi:weather-cloudy",
        enabled=False,
        options=("both", "speak", "belly"),
    ),
)

# ---------------------------------------------------------------- numbers

NUMBERS: tuple[Setting, ...] = (
    Setting(key="nightlight_level", icon="mdi:brightness-6", minimum=1, maximum=5),
    Setting(
        key="weather_belly_minutes",
        icon="mdi:timer-sand",
        enabled=False,
        minimum=0,
        maximum=1440,
        step=5,
        unit="min",
    ),
)

ALL: tuple[Setting, ...] = SWITCHES + TIMES + SELECTS + NUMBERS


def keys() -> set[str]:
    return {s.key for s in ALL}
