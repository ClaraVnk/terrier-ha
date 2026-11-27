"""The rabbit's mind: whether something in the house is worth saying.

On what a person in the room would notice (someone arriving, a machine
finishing, a shutter closing), Home Assistant's own AI decides whether the
rabbit says something, and what: the AI Task entity the owner chose, so any
provider Home Assistant knows (Clara, 2026-11-27). The house never leaves
Home Assistant: the Terrier receives only the sentence and the ears, as from
any automation. Off by default, and a rabbit speaks only once its "mind" is
set to a character other than off.

Two rules taken from domokit's first version (2026-11-27):
- the model is given causes (a shutter, a door), never the rabbit's own
  outputs, so it never reasons on what it did itself;
- every failure (no AI entity, the daily budget spent, an answer of the
  wrong shape) ends in silence, never in a guess.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any

from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .api import TerrierError
from .const import (
    CONF_BRAIN_AI,
    CONF_BRAIN_CAP,
    CONF_BRAIN_CONTEXT,
    CONF_BRAIN_WATCH,
    DEFAULT_BRAIN_CAP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CHARACTERS = ("off", "discreet", "chatty", "mischievous")
TONES = {
    "discreet": "You are discreet: you speak rarely, only when it helps, in few words.",
    "chatty": "You are chatty and warm: you like to comment on what happens, briefly.",
    "mischievous": "You are mischievous: playful, teasing, never unkind, always short.",
}
EVENT = f"{DOMAIN}_mind"
SKIP = {"unknown", "unavailable", "", "none"}
QUIET_S = 60  # one occasion per entity a minute at most
MAX_SAY = 200
EARS_MAX = 10  # 0 upright, 10 lying flat; past 10 the ear goes round

STRUCTURE = {
    "say": {
        "description": "What the rabbit says aloud, or empty to stay silent.",
        "required": False,
        "selector": {"text": {}},
    },
    "left_ear": {
        "description": "Left ear, 0 upright to 10 lying flat; leave out to keep it.",
        "required": False,
        "selector": {"number": {"min": 0, "max": EARS_MAX}},
    },
    "right_ear": {
        "description": "Right ear, 0 upright to 10 lying flat; leave out to keep it.",
        "required": False,
        "selector": {"number": {"min": 0, "max": EARS_MAX}},
    },
}


def is_occasion(old: State | None, new: State | None) -> bool:
    """A change a person would notice: a state that changed, not a reading.

    A machine that finishes is news; a power reading that moves is not, so
    a number is never an occasion, nor anything going to or from unknown.
    """
    if old is None or new is None or old.state == new.state:
        return False
    if old.state.lower() in SKIP or new.state.lower() in SKIP:
        return False
    try:
        float(new.state)
    except ValueError:
        return True
    return False


def line(state: State) -> str:
    name = state.attributes.get("friendly_name") or state.entity_id
    return f"- {name}: {state.state}"


def instructions(
    rabbit: str,
    character: str,
    occasion: str,
    context: list[str],
    now: datetime,
    language: str,
) -> str:
    """The task for the model: the character, what happened, the causes."""
    causes = "\n".join(context) or "- (nothing else known)"
    return (
        f"You are {rabbit}, a Nabaztag rabbit in this home. {TONES[character]}\n"
        f"It is {now:%A %H:%M}.\n\n"
        f"What just happened:\n{occasion}\n\n"
        f"What is known about the home right now:\n{causes}\n\n"
        "Decide whether this is worth saying out loud. Staying silent is often "
        "right: if someone may be asleep, resting or busy, or if it is not "
        "interesting, leave `say` empty. If you speak, one short sentence, "
        f"in the language whose code is {language}, without emoji. You may "
        "move your ears to show a feeling (0 upright, 10 lying flat)."
    )


def decision(data: Any) -> tuple[str, tuple[int, int] | None]:
    """(what to say, (left, right) or None) from the model's answer; an
    answer of the wrong shape is silence, never a guess."""
    if not isinstance(data, dict):
        return "", None
    say = data.get("say")
    say = " ".join(say.split())[:MAX_SAY] if isinstance(say, str) else ""
    ears = None
    left, right = data.get("left_ear"), data.get("right_ear")
    if (
        isinstance(left, (int, float))
        and isinstance(right, (int, float))
        and 0 <= left <= EARS_MAX
        and 0 <= right <= EARS_MAX
    ):
        ears = (int(left), int(right))
    return say, ears


class Budget:
    """At most `cap` calls to the model a day, shared by every rabbit."""

    def __init__(self, cap: int) -> None:
        self.cap, self.day, self.used = cap, date.today(), 0

    def take(self, today: date | None = None) -> bool:
        today = today or date.today()
        if today != self.day:
            self.day, self.used = today, 0
        if self.used >= self.cap:
            return False
        self.used += 1
        return True


class Mind:
    """Watches the chosen entities and asks the AI for each rabbit with a
    character. One instance per config entry, started in __init__."""

    def __init__(self, hass: HomeAssistant, entry: Any, coordinator: Any) -> None:
        self.hass, self.entry, self.coordinator = hass, entry, coordinator
        opts = entry.options
        self.ai = opts.get(CONF_BRAIN_AI)
        own = {
            e.entity_id
            for e in er.async_entries_for_config_entry(
                er.async_get(hass), entry.entry_id
            )
        }
        # Never its own entities: the rabbit must not read its own outputs.
        self.watch = [e for e in opts.get(CONF_BRAIN_WATCH) or [] if e not in own]
        self.context = [e for e in opts.get(CONF_BRAIN_CONTEXT) or [] if e not in own]
        self.budget = Budget(int(opts.get(CONF_BRAIN_CAP) or DEFAULT_BRAIN_CAP))
        self._last: dict[str, float] = {}

    @callback
    def start(self) -> Any:
        if not self.ai or not self.watch:
            return lambda: None
        return async_track_state_change_event(self.hass, self.watch, self._changed)

    @callback
    def _changed(self, event: Event) -> None:
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if not is_occasion(old, new):
            return
        now = time.monotonic()
        if now - self._last.get(new.entity_id, -QUIET_S) < QUIET_S:
            return
        self._last[new.entity_id] = now
        name = new.attributes.get("friendly_name") or new.entity_id
        occasion = f"- {name}: {old.state} -> {new.state}"
        self.hass.async_create_task(self._think(occasion))

    async def _think(self, occasion: str) -> None:
        characters = getattr(self.coordinator, "minds", {})
        context = [line(s) for e in self.context if (s := self.hass.states.get(e))]
        for mac, rabbit in (self.coordinator.data or {}).items():
            character = characters.get(mac, "off")
            if character not in TONES:
                continue
            name = rabbit.get("name") or mac
            if not self.budget.take():
                _LOGGER.info(
                    "mind: the day's %d calls are spent; %s stays silent",
                    self.budget.cap,
                    name,
                )
                return
            try:
                resp = await self.hass.services.async_call(
                    "ai_task",
                    "generate_data",
                    {
                        "task_name": f"{DOMAIN} mind",
                        "entity_id": self.ai,
                        "instructions": instructions(
                            name,
                            character,
                            occasion,
                            context,
                            datetime.now(),
                            self.hass.config.language or "fr",
                        ),
                        "structure": STRUCTURE,
                    },
                    blocking=True,
                    return_response=True,
                )
            except Exception as err:  # any failure is silence
                _LOGGER.warning(
                    "mind: the AI did not answer for %s (%s): silent", name, err
                )
                continue
            say, ears = decision((resp or {}).get("data"))
            # Silence is a decision too: a character is tuned by seeing what
            # it chose to keep quiet about (domokit, 2026-11-27).
            self.hass.bus.async_fire(
                EVENT, {"rabbit": name, "occasion": occasion, "say": say, "ears": ears}
            )
            try:
                if ears:
                    await self.coordinator.client.ears(mac, *ears)
                if say:
                    await self.coordinator.client.speak(mac, say)
            except TerrierError as err:
                # Asleep (409), offline (503): the Terrier refused, nothing more.
                _LOGGER.info("mind: %s did not speak: %s", name, err)
