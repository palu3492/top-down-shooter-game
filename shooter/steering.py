"""Reusable deterministic steering over Match-owned spatial state."""

import math

from shooter.match_actors import move_match_actor
from shooter.world_collision import actor_box, overlaps


def nearby_occupants(match, actor_ids, cell_size=128, limit=12):
    """Return bounded, local dynamic blockers for each actor.

    Crowd collision must never build a list containing the whole horde.  The
    surrounding grid cells contain every actor that could contact this frame;
    bounding the result keeps an extreme pile-up inexpensive as well.
    """
    cells = {}
    actor_ids = tuple(actor_id for actor_id in actor_ids if actor_id in match.spatial)
    for actor_id in actor_ids:
        transform = match.spatial.get(actor_id).transform
        cell = int(transform.x // cell_size), int(transform.y // cell_size)
        cells.setdefault(cell, []).append(actor_id)
    result = {}
    for actor_id in actor_ids:
        transform = match.spatial.get(actor_id).transform
        cell = int(transform.x // cell_size), int(transform.y // cell_size)
        candidates = [
            other_id
            for x_offset in (-1, 0, 1)
            for y_offset in (-1, 0, 1)
            for other_id in cells.get((cell[0] + x_offset, cell[1] + y_offset), ())
            if other_id != actor_id
        ]
        candidates.sort(
            key=lambda other_id: math.dist(
                (transform.x, transform.y),
                (
                    match.spatial.get(other_id).transform.x,
                    match.spatial.get(other_id).transform.y,
                ),
            )
        )
        result[actor_id] = tuple(candidates[:limit])
    return result


def pursue_match_actor(
    match, actor_id, target_id, dt, avoid_ids=(), obstacles=(), direction=None
):
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
    direction = (dx / distance, dy / distance) if direction is None else direction
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
    cells = {}
    cell_size = 128
    for actor_id in actor_ids:
        transform = match.spatial.get(actor_id).transform
        cell = int(transform.x // cell_size), int(transform.y // cell_size)
        cells.setdefault(cell, []).append(actor_id)
    compared = set()
    for cell, members in cells.items():
        nearby = [
            other
            for offset_x in (-1, 0, 1)
            for offset_y in (-1, 0, 1)
            for other in cells.get((cell[0] + offset_x, cell[1] + offset_y), ())
        ]
        for first_id in members:
            for second_id in nearby:
                if first_id == second_id:
                    continue
                pair = tuple(sorted((first_id, second_id)))
                if pair in compared:
                    continue
                compared.add(pair)
                _separate_pair(match, first_id, second_id, obstacles)


def _separate_pair(match, first_id, second_id, obstacles):
    first = match.spatial.get(first_id)
    second = match.spatial.get(second_id)
    if first.collision is None or second.collision is None:
        return
    first_box = actor_box(first.transform, first.collision)
    second_box = actor_box(second.transform, second.collision)
    if not overlaps(first_box, second_box):
        return
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
