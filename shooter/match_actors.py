"""Shared neutral actor registration and movement against Match-owned stores."""

from dataclasses import dataclass
import math

from shooter.actor_creation import NeutralActorFactory
from shooter.spatial import Bounds, Box, Transform
from shooter.spawn_service import SpawnService
from shooter.world_collision import actor_box, overlaps


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


def remove_match_actor(match, actor_id, reason="removed"):
    """Remove one actor from every shared Match-owned capability store."""
    if actor_id not in match.entities:
        return None
    if actor_id in match.spatial:
        match.spatial.remove(actor_id)
    if actor_id in match.combat:
        match.combat.remove(actor_id)
    match.factions.remove(actor_id)
    return match.entities.remove(actor_id, reason=reason)


def move_match_actor(match, actor_id, direction, dt, occupied_ids=(), obstacles=()):
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
    bounds = Bounds(
        half_width, half_height, width - half_width, height - half_height
    )
    delta_x = dx * actor.movement_speed * dt
    delta_y = dy * actor.movement_speed * dt
    collision = match.spatial.get(actor_id).collision
    obstacles = (
        *match.map_definition.collision,
        *tuple(obstacles),
        *(
            actor_box(
                match.spatial.get(occupied_id).transform,
                match.spatial.get(occupied_id).collision,
            )
            for occupied_id in occupied_ids
            if occupied_id != actor_id
            and occupied_id in match.spatial
            and match.spatial.get(occupied_id).collision is not None
        ),
    )
    if collision is None or not obstacles:
        target = bounds.clamp(Transform(current.x + delta_x, current.y + delta_y))
        return match.spatial.move_to(actor_id, target.x, target.y)

    step_limit = max(1.0, min(actor.collision_size) / 2)
    steps = max(1, math.ceil(max(abs(delta_x), abs(delta_y)) / step_limit))
    position = current
    for _ in range(steps):
        next_x = bounds.clamp(
            Transform(position.x + delta_x / steps, position.y)
        )
        position = _resolve_step(position, next_x, collision, obstacles)
        next_y = bounds.clamp(
            Transform(position.x, position.y + delta_y / steps)
        )
        position = _resolve_step(position, next_y, collision, obstacles)
    return match.spatial.move_to(actor_id, position.x, position.y)


def _resolve_step(start, target, collision, obstacles):
    if not _blocked(target, collision, obstacles):
        return target
    safe, blocked = start, target
    for _ in range(20):
        midpoint = Transform(
            (safe.x + blocked.x) / 2,
            (safe.y + blocked.y) / 2,
        )
        if _blocked(midpoint, collision, obstacles):
            blocked = midpoint
        else:
            safe = midpoint
    return safe


def _blocked(transform, collision, obstacles):
    box = actor_box(transform, collision)
    return any(overlaps(box, obstacle) for obstacle in obstacles)
