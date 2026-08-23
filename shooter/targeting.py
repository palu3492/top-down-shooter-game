"""Deterministic pygame-free target selection in authoritative world space."""

import math

from shooter.spatial import Box
from shooter.world_collision import actor_box


def first_box_target_on_ray(match, origin, direction, candidate_ids, max_distance):
    """Return the nearest ray-hit candidate, with entity ID as the tie-breaker."""
    magnitude = math.hypot(*direction)
    if magnitude == 0 or max_distance < 0:
        return None
    unit = (direction[0] / magnitude, direction[1] / magnitude)
    hits = []
    for entity_id in candidate_ids:
        if entity_id not in match.spatial:
            continue
        state = match.spatial.get(entity_id)
        if not isinstance(state.collision, Box):
            continue
        box = actor_box(state.transform, state.collision)
        distance = _ray_aabb_distance(origin, unit, box)
        if distance is not None and distance <= max_distance:
            hits.append((distance, int(entity_id), entity_id))
    return None if not hits else min(hits)[2]


def _ray_aabb_distance(origin, direction, box):
    near, far = 0.0, math.inf
    for start, step, lower, upper in (
        (origin[0], direction[0], box.left, box.right),
        (origin[1], direction[1], box.top, box.bottom),
    ):
        if step == 0:
            if start < lower or start > upper:
                return None
            continue
        first, second = (lower - start) / step, (upper - start) / step
        axis_near, axis_far = min(first, second), max(first, second)
        near, far = max(near, axis_near), min(far, axis_far)
        if near > far:
            return None
    return near if far >= 0 else None
