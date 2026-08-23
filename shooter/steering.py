"""Reusable deterministic steering over Match-owned spatial state."""

import math

from shooter.match_actors import move_match_actor
from shooter.world_collision import actor_box, overlaps


def pursue_match_actor(match, actor_id, target_id, dt, avoid_ids=(), obstacles=()):
    """Move toward a target, choosing a stable side when direct travel is blocked."""
    if dt < 0:
        raise ValueError("dt cannot be negative")
    if actor_id not in match.spatial or target_id not in match.spatial:
        return None
    start = match.spatial.get(actor_id).transform
    target = match.spatial.get(target_id).transform
    dx, dy = target.x - start.x, target.y - start.y
    distance = math.hypot(dx, dy)
    if distance == 0:
        return match.spatial.get(actor_id)
    speed = match.entities.get(actor_id).movement_speed
    if speed <= 0:
        return match.spatial.get(actor_id)
    travel_dt = min(dt, distance / speed)
    direction = (dx / distance, dy / distance)
    occupied = tuple(avoid_ids)
    moved = move_match_actor(
        match, actor_id, direction, travel_dt, occupied, obstacles
    )
    if moved is None or travel_dt == 0:
        return moved
    travelled = (
        abs(moved.transform.x - start.x)
        if abs(direction[0]) >= abs(direction[1])
        else abs(moved.transform.y - start.y)
    )
    expected = speed * travel_dt
    primary = max(abs(direction[0]), abs(direction[1]))
    if travelled >= expected * primary * 0.25:
        return moved

    match.spatial.move_to(actor_id, start.x, start.y)

    left = (-direction[1], direction[0])
    right = (direction[1], -direction[0])
    alternatives = (left, right) if int(actor_id) % 2 else (right, left)
    for alternative in alternatives:
        moved = move_match_actor(
            match, actor_id, alternative, travel_dt, occupied, obstacles
        )
        if moved is not None and moved.transform != start:
            return moved
    return moved


def separate_overlapping_actors(match, actor_ids, obstacles=()):
    """Resolve crowd overlap before pursuit so avoidance cannot deadlock."""
    actor_ids = tuple(actor_id for actor_id in actor_ids if actor_id in match.spatial)
    for index, first_id in enumerate(actor_ids):
        for second_id in actor_ids[index + 1 :]:
            first = match.spatial.get(first_id)
            second = match.spatial.get(second_id)
            if first.collision is None or second.collision is None:
                continue
            first_box = actor_box(first.transform, first.collision)
            second_box = actor_box(second.transform, second.collision)
            if not overlaps(first_box, second_box):
                continue
            horizontal = min(first_box.right, second_box.right) - max(
                first_box.left, second_box.left
            )
            vertical = min(first_box.bottom, second_box.bottom) - max(
                first_box.top, second_box.top)
            if horizontal <= vertical:
                direction = -1 if first.transform.x <= second.transform.x else 1
                offset = (direction * (horizontal / 2 + 0.5), 0)
            else:
                direction = -1 if first.transform.y <= second.transform.y else 1
                offset = (0, direction * (vertical / 2 + 0.5))
            _move_if_clear(match, first_id, offset, obstacles)
            _move_if_clear(match, second_id, (-offset[0], -offset[1]), obstacles)


def _move_if_clear(match, actor_id, offset, obstacles):
    state = match.spatial.get(actor_id)
    actor = match.entities.get(actor_id)
    width, height = match.map_definition.size
    x = min(
        max(actor.collision_size[0] / 2, state.transform.x + offset[0]),
        width - actor.collision_size[0] / 2,
    )
    y = min(
        max(actor.collision_size[1] / 2, state.transform.y + offset[1]),
        height - actor.collision_size[1] / 2,
    )
    candidate = type(state.transform)(x, y)
    obstacles = (*match.map_definition.collision, *obstacles)
    blocked = any(
        overlaps(actor_box(candidate, state.collision), obstacle)
        for obstacle in obstacles
    )
    if not blocked:
        match.spatial.move_to(actor_id, x, y)
