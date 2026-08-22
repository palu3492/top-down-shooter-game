"""Neutral first vertical slice of Zombie Survival rules."""

from dataclasses import dataclass
import math

from shooter import config
from shooter.actor_creation import ActorDefinition
from shooter.damage import DamageRequest
from shooter.match_actors import move_match_actor, spawn_match_actors
from shooter.modes.zombie_survival.state import LOST, SurvivalStatus
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import SpawnActorRequest
from shooter.world_collision import Aabb

SURVIVOR = ActorDefinition(
    "survivor",
    "soldier",
    "survivors",
    config.PLAYER_HEALTH,
    (48, 48),
    config.PLAYER_SPEED,
)
WALKER = ActorDefinition(
    "walker", "walker", "horde", config.ZOMBIE_HEALTH, (56, 56), config.ZOMBIE_SPEED
)


@dataclass(frozen=True, slots=True)
class MoveSurvivor:
    direction: tuple[float, float]


@dataclass(frozen=True, slots=True)
class DamageEnemy:
    target_id: int
    amount: float
    damage_type: str = "survivor_attack"


class SurvivalMode:
    """Shared-runtime Survival state, initially one player and one enemy wave."""

    def __init__(self, spawn_sources=(), enemy_count=None):
        self.spawn_sources = tuple(spawn_sources)
        self.enemy_count = config.WAVE_BASE if enemy_count is None else enemy_count
        self.player_id = None
        self.enemy_ids = ()
        self.spawn_results = ()
        self.disposed = False

    def start(self, match):
        width, height = match.map_definition.size
        common = {
            "bounds": Aabb(0, 0, width, height),
            "collision": match.map_definition.collision,
        }
        player = spawn_match_actors(
            match,
            SpawnActorRequest(
                SURVIVOR,
                SpawnQuery(
                    role="player", faction="survivors", actor_kind="soldier"
                ),
                PlacementConstraints(
                    footprint=SURVIVOR.collision_size,
                    **common,
                ),
                1,
            ),
            self.spawn_sources,
            "survival-player-spawns",
            tags=("player",),
        )
        enemies = spawn_match_actors(
            match,
            SpawnActorRequest(
                WALKER,
                SpawnQuery(role="enemy", faction="horde", actor_kind="walker"),
                PlacementConstraints(
                    footprint=WALKER.collision_size,
                    minimum_occupant_distance=max(WALKER.collision_size),
                    **common,
                ),
                self.enemy_count,
            ),
            self.spawn_sources,
            "survival-enemy-spawns",
            tags=("enemy",),
        )
        self.player_id = player.actor_ids[0] if player.actor_ids else None
        self.enemy_ids = enemies.actor_ids
        self.spawn_results = (player.spawn_result, enemies.spawn_result)

    def advance(self, match, commands, dt):
        if dt < 0:
            raise ValueError("dt cannot be negative")
        for command in commands:
            if isinstance(command, MoveSurvivor) and self.player_id is not None:
                move_match_actor(match, self.player_id, command.direction, dt)
            elif isinstance(command, DamageEnemy) and self.player_id is not None:
                match.damage.apply(
                    DamageRequest(
                        self.player_id,
                        self.player_id,
                        command.target_id,
                        command.amount,
                        command.damage_type,
                        match.tick,
                    )
                )
        self._advance_enemies(match, dt)

    def status(self, match):
        return SurvivalStatus(
            phase="combat" if self.enemies_remaining(match) else "preparation",
            wave=1,
            preparation_remaining=0.0,
            cash=0,
            enemies_remaining=self.enemies_remaining(match),
            outcome=self.result(match),
        )

    def result(self, match):
        if self.player_id is None or self.player_id not in match.combat:
            return None
        return None if match.combat.get(self.player_id).alive else LOST

    def dispose(self, match):
        self.disposed = True

    def enemies_remaining(self, match):
        return sum(
            match.combat.get(enemy_id).alive
            for enemy_id in self.enemy_ids
            if enemy_id in match.combat
        )

    def _advance_enemies(self, match, dt):
        if self.player_id is None or self.player_id not in match.spatial:
            return
        target = match.spatial.get(self.player_id).transform
        for enemy_id in self.enemy_ids:
            if enemy_id not in match.spatial or not match.combat.get(enemy_id).alive:
                continue
            current = match.spatial.get(enemy_id).transform
            dx, dy = target.x - current.x, target.y - current.y
            distance = math.hypot(dx, dy)
            direction = (0, 0) if distance == 0 else (dx / distance, dy / distance)
            move_match_actor(match, enemy_id, direction, dt)
