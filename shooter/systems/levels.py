"""Freeplay as numbered levels rather than a curve that runs forever.

A level is the wave system with a finish line. `WaveSystem` already decides what
spawns and when; this adds a target and declares a win when it is met, which is
the whole of what AT31's outcome seam was for.

The levels are a table rather than a formula. A formula is tempting and gives
every level the same shape -- the point of authoring them is that the third one
can be a step up rather than four per cent harder than the second.
"""

from dataclasses import dataclass
from functools import partial

from shooter import config
from shooter.actor_adapter import LegacyActorFactory
from shooter.session import WON
from shooter.systems import world
from shooter.systems.waves import WaveSystem
from shooter.ui.anchor import CENTRE, TOP, place


@dataclass(frozen=True)
class Level:
    """What a level asks of the player."""

    number: int
    waves: int
    opening: int
    growth: int
    props: tuple = world.STARTER

    @property
    def title(self):
        return f"LEVEL {self.number}"


LEVELS = (
    Level(number=1, waves=3, opening=4, growth=2),
    Level(number=2, waves=4, opening=5, growth=3),
    Level(number=3, waves=5, opening=7, growth=4),
    Level(number=4, waves=6, opening=9, growth=5),
    Level(number=5, waves=8, opening=12, growth=6),
)

FIRST = LEVELS[0]

BANNER_SIZE = (500, 60)
BANNER_INSET = (0, 150)


def level_number(number):
    """The level with this number, or the last one repeated.

    Freeplay does not run out: past the authored levels the hardest one is
    played again rather than the game refusing to start.
    """
    for level in LEVELS:
        if level.number == number:
            return level
    return LEVELS[-1]


def rules_for(level):
    """A rules factory `Session` can call with its own four arguments."""
    return partial(LevelRules, level=level)


class LevelRules(WaveSystem):
    """Waves until the level's target is cleared."""

    def __init__(
        self,
        window,
        zombie_group,
        player_cash,
        visible=None,
        level=FIRST,
        actor_factory=None,
    ):
        self.level = level
        self.cleared = 0
        self.wave_count = 0
        self.wave_seconds = 0.0
        self.actor_factory = actor_factory or LegacyActorFactory()
        self._spawn(window, zombie_group, player_cash, visible, self.level.opening)

    @property
    def layout(self):
        """What stands in this level. A level owns its world, not the mode."""
        return self.level.props

    @property
    def outcome(self):
        return WON if self.cleared >= self.level.waves else None

    @property
    def wave(self):
        """Which wave is being fought, counting from one."""
        return min(self.cleared + 1, self.level.waves)

    def advance(
        self, window, zombie_group, player_cash, dt=config.SIM_DT, visible=None
    ):
        """Called with the field clear, so arriving here means a wave is done."""
        if self.outcome is not None:
            return

        if self._consume_skip():
            self.wave_seconds = config.WAVE_INTERVAL_SECONDS
        if self.wave_seconds >= config.WAVE_INTERVAL_SECONDS:
            self.cleared += 1
            self.wave_count = self.cleared
            self.wave_seconds = 0.0
            if self.outcome is None:
                self._spawn(
                    window,
                    zombie_group,
                    player_cash,
                    visible,
                    self.level.opening + self.cleared * self.level.growth,
                )
        else:
            self.wave_seconds += dt

    def _spawn(self, window, zombie_group, player_cash, visible, count):
        if not config.ZOMBIE_SPAWNING_ENABLED:
            return
        for _ in range(count):
            zombie_group.add(self.actor_factory.spawn_walker(window, visible))

    def draw(self, screen, window=config.WINDOW):
        """Between waves, say where the player is in the level.

        The endless banner counted down to a round that would always come; this
        has somewhere to be counting towards.
        """
        if self.outcome is not None:
            return

        remaining = max(0, int(config.WAVE_INTERVAL_SECONDS - self.wave_seconds))
        banner = place(BANNER_SIZE, window, CENTRE, TOP, BANNER_INSET)
        self._centred(
            screen,
            f"{self.level.title}  --  WAVE {self.wave} OF {self.level.waves}",
            banner,
            0,
        )
        self._centred(screen, f"next in {remaining}, or [SPACE]", banner, 30)
