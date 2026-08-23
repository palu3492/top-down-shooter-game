"""Reusable deterministic steering over Match-owned spatial state."""

import math

from shooter.match_actors import move_match_actor


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
