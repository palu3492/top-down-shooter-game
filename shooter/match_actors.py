"""Shared neutral actor registration and movement against Match-owned stores."""

from dataclasses import dataclass
import math

from shooter.actor_creation import NeutralActorFactory
from shooter.spatial import Bounds, Box, Transform
from shooter.spawn_service import SpawnService


@dataclass(frozen=True, slots=True)
class RegisteredSpawnBatch:
    actor_ids: tuple[int, ...]
    spawn_result: object


def spawn_match_actors(match, request, sources, stream_name, tags=()):
    result = SpawnService(
        NeutralActorFactory(), match.random_stream(stream_name)
    ).spawn(request, sources, match.map_definition.size)
    actor_ids = []
    for actor in result.actors:
        actor_id = match.entities.register(
            actor, ("actor", actor.faction, *tuple(tags))
        )
        match.spatial.attach(
            actor_id,
            Transform(*actor.position),
            Box(*actor.collision_size),
        )
        match.combat.attach(actor_id, actor.max_health)
        match.factions.assign(actor_id, actor.faction)
        actor_ids.append(actor_id)
    return RegisteredSpawnBatch(tuple(actor_ids), result)


def move_match_actor(match, actor_id, direction, dt):
    if actor_id not in match.spatial:
        return None
    actor = match.entities.get(actor_id)
    dx, dy = direction
    magnitude = math.hypot(dx, dy)
    if magnitude > 1:
        dx, dy = dx / magnitude, dy / magnitude
    current = match.spatial.get(actor_id).transform
    half_width = actor.collision_size[0] / 2
    half_height = actor.collision_size[1] / 2
    width, height = match.map_definition.size
    bounded = Bounds(
        half_width, half_height, width - half_width, height - half_height
    ).clamp(
        Transform(
            current.x + dx * actor.movement_speed * dt,
            current.y + dy * actor.movement_speed * dt,
        )
    )
    return match.spatial.move_to(actor_id, bounded.x, bounded.y)
