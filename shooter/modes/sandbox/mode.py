"""Headless lifecycle and status for the architecture's reuse proof."""

from dataclasses import dataclass

from shooter.actor_creation import ActorDefinition
from shooter.damage import DamageRequest
from shooter.match_actors import move_match_actor, spawn_match_actors
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import SpawnActorRequest
from shooter.world_collision import Aabb

COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class SandboxStatus:
    elapsed: float
    advances: int
    outcome: str | None = None
    actors_alive: int = 0
    title: str = "Sandbox"


@dataclass(frozen=True, slots=True)
class MoveActor:
    actor_id: int
    direction: tuple[float, float]


@dataclass(frozen=True, slots=True)
class AttackActor:
    instigator_id: int
    target_id: int
    amount: float
    damage_type: str = "sandbox"


RED_ACTOR = ActorDefinition("red_actor", "soldier", "red", 100, (32, 32), 160)
BLUE_ACTOR = ActorDefinition("blue_actor", "soldier", "blue", 100, (32, 32), 160)


class SandboxMode:
    """A deliberately tiny mode with no zombie or presentation policy."""

    def __init__(self, duration_seconds=None, spawn_sources=()):
        if duration_seconds is not None and duration_seconds < 0:
            raise ValueError("duration_seconds cannot be negative")
        self.duration_seconds = duration_seconds
        self.elapsed = 0.0
        self.advances = 0
        self.started = False
        self.disposed = False
        self.spawn_sources = tuple(spawn_sources)
        self.actor_ids = {}
        self.spawn_results = ()

    def start(self, match):
        self.started = True
        spawned = []
        width, height = match.map_definition.size
        occupied = []
        for definition in (RED_ACTOR, BLUE_ACTOR):
            request = SpawnActorRequest(
                definition,
                SpawnQuery(
                    role="player",
                    faction=definition.faction,
                    actor_kind=definition.actor_kind,
                ),
                PlacementConstraints(
                    bounds=Aabb(0, 0, width, height),
                    occupied=tuple(occupied),
                    minimum_occupant_distance=definition.collision_size[0],
                    collision=match.map_definition.collision,
                    footprint=definition.collision_size,
                ),
                count=1,
            )
            registered = spawn_match_actors(
                match,
                request,
                self.spawn_sources,
                "sandbox-spawns",
                tags=("player",),
            )
            result = registered.spawn_result
            spawned.append(result)
            for actor_id, actor in zip(
                registered.actor_ids, result.actors, strict=True
            ):
                self.actor_ids[actor.faction] = actor_id
                occupied.append(actor.position)
        self.spawn_results = tuple(spawned)

    def advance(self, match, commands, dt):
        if dt < 0:
            raise ValueError("dt cannot be negative")
        self.advances += 1
        self.elapsed += dt
        for command in commands:
            if isinstance(command, MoveActor):
                move_match_actor(match, command.actor_id, command.direction, dt)
            elif isinstance(command, AttackActor):
                match.damage.apply(
                    DamageRequest(
                        command.instigator_id,
                        command.instigator_id,
                        command.target_id,
                        command.amount,
                        command.damage_type,
                        match.tick,
                    )
                )

    def status(self, match):
        alive = sum(
            match.combat.get(actor_id).alive
            for actor_id in self.actor_ids.values()
            if actor_id in match.combat
        )
        return SandboxStatus(self.elapsed, self.advances, self.result(match), alive)

    def result(self, match):
        if self.duration_seconds is None or self.elapsed < self.duration_seconds:
            return None
        return COMPLETE

    def dispose(self, match):
        self.disposed = True
