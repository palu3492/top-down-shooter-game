"""Small, pygame-independent values describing player intent.

These are local commands today. Keeping them immutable and limited to primitive
values lets tests, replays, and a future network adapter produce the same input.
"""

from dataclasses import dataclass

FIRE = "fire"
RELOAD = "reload"
INTERACT = "interact"
USE_GRENADE = "use_grenade"
USE_STUN_GRENADE = "use_stun_grenade"
SKIP_PHASE = "skip_phase"
GRANT_ALL = "grant_all"
SELECT_SLOT = "select_slot"
SLOT_COUNT = 5


@dataclass(frozen=True, slots=True)
class ActionCommand:
    """One discrete action, optionally carrying one integer argument."""

    action: str
    value: int | None = None


@dataclass(frozen=True, slots=True)
class ControlFrame:
    """Continuous intent sampled once and reused for fixed simulation steps."""

    move: tuple[int, int] = (0, 0)
    aim: tuple[int, int] = (0, 0)
    trigger_held: bool = False
