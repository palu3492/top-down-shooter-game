"""Deterministic queries over neutral map-authored interactions."""

import math

from shooter.world_collision import Aabb, Ellipse, Polygon


def nearest_interaction(
    interactions, position, max_distance, *, kind=None, required_tags=()
):
    if max_distance < 0:
        raise ValueError("max_distance cannot be negative")
    required_tags = frozenset(required_tags)
    matches = []
    for interaction in interactions:
        if kind is not None and interaction.kind != kind:
            continue
        if not required_tags <= interaction.tags:
            continue
        distance = interaction_distance(interaction, position)
        if distance <= max_distance:
            matches.append((distance, interaction.interaction_id, interaction))
    return None if not matches else min(matches)[2]


def interaction_distance(interaction, position):
    if interaction.position is not None:
        return math.dist(interaction.position, position)
    bounds = _bounds(interaction.area)
    nearest_x = min(max(position[0], bounds.left), bounds.right)
    nearest_y = min(max(position[1], bounds.top), bounds.bottom)
    return math.dist(position, (nearest_x, nearest_y))


def _bounds(area):
    if isinstance(area, Aabb):
        return area
    if isinstance(area, Ellipse):
        return Aabb(area.x, area.y, area.width, area.height)
    if isinstance(area, Polygon):
        return Aabb(
            min(x for x, _ in area.points),
            min(y for _, y in area.points),
            max(x for x, _ in area.points) - min(x for x, _ in area.points),
            max(y for _, y in area.points) - min(y for _, y in area.points),
        )
    raise TypeError(f"unsupported interaction area: {type(area).__name__}")
