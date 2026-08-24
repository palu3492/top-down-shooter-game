"""Shared neutral actor registration and movement against Match-owned stores."""

from dataclasses import dataclass
from functools import cache
import math

from shooter.actor_creation import NeutralActorFactory
from shooter.spatial import Bounds, Box, Transform
from shooter.spawn_service import SpawnService
from shooter.world_collision import Aabb, Polygon, actor_box, bounds_of, contains, overlaps


@dataclass(frozen=True, slots=True)
class RegisteredSpawnBatch:
    actor_ids: tuple[int, ...]
    spawn_result: object


@cache
def _static_obstacle_bounds(obstacles):
    """Cache broad-phase bounds for immutable map geometry.

    Dynamic actors and barricades are deliberately excluded: their positions can
    change between movement calls, while authored TMX geometry cannot.
    """
    return tuple((obstacle, bounds_of(obstacle)) for obstacle in obstacles)


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
    playable_areas = match.map_definition.playable_areas
    dynamic_obstacles = (
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
    travel_area = Aabb(
        min(current.x, current.x + delta_x) - half_width,
        min(current.y, current.y + delta_y) - half_height,
        abs(delta_x) + actor.collision_size[0],
        abs(delta_y) + actor.collision_size[1],
    )
    obstacles = tuple(
        obstacle
        for obstacle, obstacle_bounds in (
            *_static_obstacle_bounds(match.map_definition.collision),
            *((obstacle, bounds_of(obstacle)) for obstacle in dynamic_obstacles),
        )
        if overlaps(travel_area, obstacle_bounds)
    )
    if collision is None or (not obstacles and not playable_areas):
        target = bounds.clamp(Transform(current.x + delta_x, current.y + delta_y))
        return match.spatial.move_to(actor_id, target.x, target.y)

    step_limit = max(1.0, min(actor.collision_size) / 2)
    steps = max(1, math.ceil(max(abs(delta_x), abs(delta_y)) / step_limit))
    position = current
    for _ in range(steps):
        next_x = bounds.clamp(
            Transform(position.x + delta_x / steps, position.y)
        )
        blocked_x = _blocked(next_x, collision, obstacles, playable_areas)
        position = _resolve_step(position, next_x, collision, obstacles, playable_areas)
        next_y = bounds.clamp(
            Transform(position.x, position.y + delta_y / steps)
        )
        blocked_y = _blocked(next_y, collision, obstacles, playable_areas)
        position = _resolve_step(position, next_y, collision, obstacles, playable_areas)
        if blocked_x or blocked_y:
            slid = _slide_step(
                position,
                delta_x / steps,
                delta_y / steps,
                bounds,
                collision,
                obstacles,
                playable_areas,
            )
            if slid != position:
                position = slid
    return match.spatial.move_to(actor_id, position.x, position.y)


def _resolve_step(start, target, collision, obstacles, playable_areas=()):
    if not _blocked(target, collision, obstacles, playable_areas):
        return target
    safe, blocked = start, target
    for _ in range(20):
        midpoint = Transform(
            (safe.x + blocked.x) / 2,
            (safe.y + blocked.y) / 2,
        )
        if _blocked(midpoint, collision, obstacles, playable_areas):
            blocked = midpoint
        else:
            safe = midpoint
    return safe


def _blocked(transform, collision, obstacles, playable_areas=()):
    box = actor_box(transform, collision)
    return any(overlaps(box, obstacle) for obstacle in obstacles) or (
        bool(playable_areas) and not any(contains(area, box) for area in playable_areas)
    )


def _slide_step(start, delta_x, delta_y, bounds, collision, obstacles, playable_areas=()):
    """Try either tangent when movement directly into a collider is blocked."""
    if delta_x == 0 and delta_y == 0:
        return start
    forward = Transform(start.x + delta_x, start.y + delta_y)
    blocking_shapes = [
        obstacle
        for obstacle in obstacles
        if overlaps(actor_box(forward, collision), obstacle)
    ]
    blocking_shapes.extend(
        area
        for area in playable_areas
        if not contains(area, actor_box(forward, collision))
    )
    offsets = [
        offset
        for obstacle in blocking_shapes
        for offset in _polygon_tangents(start, obstacle, (delta_x, delta_y))
    ]
    offsets.sort(
        key=lambda offset: offset[0] * delta_x + offset[1] * delta_y,
        reverse=True,
    )
    for offset in offsets:
        candidate = bounds.clamp(Transform(start.x + offset[0], start.y + offset[1]))
        if candidate != start and not _blocked(
            candidate, collision, obstacles, playable_areas
        ):
            return candidate
    return start


def _polygon_tangents(position, obstacle, movement):
    """Return the movement component parallel to the nearest polygon edge."""
    if not isinstance(obstacle, Polygon):
        return ()
    edges = tuple(
        zip(obstacle.points, (*obstacle.points[1:], obstacle.points[0]), strict=True)
    )
    start, end = min(edges, key=lambda edge: _segment_distance(position, *edge))
    length = math.dist(start, end)
    if length == 0:
        return ()
    tangent = ((end[0] - start[0]) / length, (end[1] - start[1]) / length)
    projection = movement[0] * tangent[0] + movement[1] * tangent[1]
    if projection == 0:
        return ()
    return ((tangent[0] * projection, tangent[1] * projection),)


def _segment_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.dist(point, start)
    projection = (
        (point.x - start[0]) * dx + (point.y - start[1]) * dy
    ) / length_squared
    progress = min(1, max(0, projection))
    return math.dist(
        (point.x, point.y),
        (start[0] + dx * progress, start[1] + dy * progress),
    )
