"""Zombie Survival wave scheduling and enemy-composition policy."""

from shooter import config
from shooter.actor_adapter import LegacyActorFactory, walker_definition
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import LEGACY_VISIBLE_RING, SpawnActorRequest, SpawnService
from shooter.modes.zombie_survival.state import SurvivalStatus
from shooter.systems import world


class WaveSystem:
    """Zombie Survival wave state, scheduling, and composition policy."""

    outcome = None
    level = None
    layout = world.STARTER

    def __init__(
        self,
        window,
        zombie_group,
        player_cash,
        visible=None,
        actor_factory=None,
        spawn_service=None,
        spawn_sources=(),
    ):
        self.wave_count = 0
        self.wave_seconds = 0.0
        self._skip_requested = False
        self.actor_factory = actor_factory or LegacyActorFactory()
        self.spawn_service = spawn_service or SpawnService(
            self.actor_factory, self.actor_factory.rng
        )
        self.spawn_sources = tuple(spawn_sources)
        self.last_spawn_result = None
        self._spawn_actors(window, zombie_group, visible, config.WAVE_BASE)

    def advance(
        self, window, zombie_group, player_cash, dt=config.SIM_DT, visible=None
    ):
        if self._consume_skip():
            self.wave_seconds = config.WAVE_INTERVAL_SECONDS
        if self.wave_seconds >= config.WAVE_INTERVAL_SECONDS:
            self.wave_count += 1
            self._spawn_actors(
                window,
                zombie_group,
                visible,
                config.WAVE_BASE + pow(self.wave_count, 2),
            )
            self.wave_seconds = 0.0
        else:
            self.wave_seconds += dt

    def request_skip(self):
        self._skip_requested = True

    def status(self, *, cash=0, enemies_remaining=0, outcome=None):
        return SurvivalStatus(
            phase="combat" if enemies_remaining else "preparation",
            wave=self.wave_count + 1,
            preparation_remaining=max(
                0.0, config.WAVE_INTERVAL_SECONDS - self.wave_seconds
            ),
            cash=cash,
            enemies_remaining=enemies_remaining,
            outcome=outcome,
        )

    def _consume_skip(self):
        requested = getattr(self, "_skip_requested", False)
        self._skip_requested = False
        return requested

    def _spawn_actors(self, window, zombie_group, visible, count):
        definition = walker_definition()
        self.last_spawn_result = self.spawn_service.spawn(
            SpawnActorRequest(
                definition=definition,
                query=SpawnQuery(role="enemy"),
                constraints=PlacementConstraints(
                    visible_area=_visible_area(visible),
                    exclude_visible=visible is not None,
                    footprint=definition.collision_size,
                    minimum_occupant_distance=max(definition.collision_size),
                ),
                count=count,
                fallback_policy=LEGACY_VISIBLE_RING,
            ),
            self.spawn_sources,
            window,
            visible,
        )
        zombie_group.add(self.last_spawn_result.actors)
        return self.last_spawn_result

def _visible_area(visible):
    if visible is None:
        return None
    from shooter.world_collision import Aabb

    return Aabb(visible.left, visible.top, visible.width, visible.height)
