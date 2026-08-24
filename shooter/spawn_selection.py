"""Deterministic, headless spawn queries and placement constraints."""

import math
from dataclasses import dataclass

from shooter.map_definition import SpawnPoint
from shooter.world_collision import Aabb, Ellipse, Polygon, contains, overlaps

NO_SOURCES = "no_sources"
NO_VALID_POSITION = "no_valid_position"


@dataclass(frozen=True, slots=True)
class SpawnQuery:
    role: str | None = None
    required_tags: frozenset[str] = frozenset()
    faction: str | None = None
    actor_kind: str | None = None

    def matches(self, source):
        return (
            (self.role is None or source.role == self.role)
            and self.required_tags <= source.tags
            and (self.faction is None or source.faction == self.faction)
            and (self.actor_kind is None or source.actor_kind == self.actor_kind)
        )


@dataclass(frozen=True, slots=True)
class PlacementConstraints:
    bounds: Aabb | None = None
    visible_area: Aabb | None = None
    exclude_visible: bool = False
    reference: tuple[float, float] | None = None
    minimum_distance: float = 0.0
    maximum_distance: float | None = None
    occupied: tuple[tuple[float, float], ...] = ()
    minimum_occupant_distance: float = 0.0
    collision: tuple[Aabb | Ellipse | Polygon, ...] = ()
    footprint: tuple[float, float] = (0.0, 0.0)
    playable_areas: tuple[Aabb | Ellipse | Polygon, ...] = ()

    def accepts(self, position):
        footprint = _footprint(position, self.footprint)
        if self.bounds is not None and not _contains(self.bounds, footprint):
            return False
        if self.playable_areas and not any(
            contains(area, footprint) for area in self.playable_areas
        ):
            return False
        if (
            self.exclude_visible
            and self.visible_area is not None
            and overlaps(footprint, self.visible_area)
        ):
            return False
        if self.reference is not None:
            distance = math.dist(position, self.reference)
            if distance < self.minimum_distance:
                return False
            if self.maximum_distance is not None and distance > self.maximum_distance:
                return False
        if any(
            math.dist(position, occupied) < self.minimum_occupant_distance
            for occupied in self.occupied
        ):
            return False
        return not any(overlaps(footprint, obstacle) for obstacle in self.collision)


@dataclass(frozen=True, slots=True)
class SpawnSelection:
    position: tuple[float, float] | None
    spawn_id: str | None = None
    reason: str | None = None

    @property
    def selected(self):
        return self.position is not None


class SpawnSelector:
    def select(
        self,
        sources,
        query,
        constraints,
        rng,
        attempts_per_region=32,
    ):
        candidates = tuple(source for source in sources if query.matches(source))
        if not candidates:
            return SpawnSelection(None, reason=NO_SOURCES)

        remaining = list(candidates)
        while remaining:
            weights = [max(0.0, getattr(source, "weight", 1.0)) for source in remaining]
            if not any(weights):
                weights = None
            source = rng.choices(remaining, weights=weights, k=1)[0]
            remaining.remove(source)
            attempts = 1 if isinstance(source, SpawnPoint) else attempts_per_region
            for _ in range(attempts):
                position = _sample(source, rng)
                if position is not None and constraints.accepts(position):
                    return SpawnSelection(position, source.spawn_id)
        return SpawnSelection(None, reason=NO_VALID_POSITION)


def _sample(source, rng):
    if isinstance(source, SpawnPoint):
        return source.position
    area = source.area
    if isinstance(area, Aabb):
        return (
            rng.uniform(area.left, area.right),
            rng.uniform(area.top, area.bottom),
        )
    if isinstance(area, Ellipse):
        radius = math.sqrt(rng.random())
        angle = rng.uniform(0, math.tau)
        return (
            area.x + area.width / 2 + math.cos(angle) * area.width / 2 * radius,
            area.y + area.height / 2 + math.sin(angle) * area.height / 2 * radius,
        )
    if isinstance(area, Polygon):
        bounds = _polygon_bounds(area)
        for _ in range(32):
            point = (
                rng.uniform(bounds.left, bounds.right),
                rng.uniform(bounds.top, bounds.bottom),
            )
            if _point_in_polygon(point, area.points):
                return point
        return None
    raise TypeError(f"unsupported spawn region: {type(area).__name__}")


def _footprint(position, size):
    width, height = size
    return Aabb(position[0] - width / 2, position[1] - height / 2, width, height)


def _contains(bounds, box):
    return (
        box.left >= bounds.left
        and box.right <= bounds.right
        and box.top >= bounds.top
        and box.bottom <= bounds.bottom
    )


def _polygon_bounds(area):
    xs = tuple(point[0] for point in area.points)
    ys = tuple(point[1] for point in area.points)
    return Aabb(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _point_in_polygon(point, vertices):
    x, y = point
    inside = False
    previous = vertices[-1]
    for current in vertices:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing:
                inside = not inside
        previous = current
    return inside
