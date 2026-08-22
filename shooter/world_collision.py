"""Headless collision primitives in authoritative world coordinates."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Aabb:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def corners(self):
        return (
            (self.left, self.top),
            (self.right, self.top),
            (self.right, self.bottom),
            (self.left, self.bottom),
        )


@dataclass(frozen=True, slots=True)
class Ellipse:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class Polygon:
    points: tuple[tuple[float, float], ...]


def actor_box(transform, shape):
    return Aabb(
        transform.x + shape.offset_x - shape.width / 2,
        transform.y + shape.offset_y - shape.height / 2,
        shape.width,
        shape.height,
    )


def overlaps(box, obstacle):
    if isinstance(obstacle, Aabb):
        return (
            box.left < obstacle.right
            and box.right > obstacle.left
            and box.top < obstacle.bottom
            and box.bottom > obstacle.top
        )
    if isinstance(obstacle, Ellipse):
        radius_x = obstacle.width / 2
        radius_y = obstacle.height / 2
        if radius_x <= 0 or radius_y <= 0:
            return False
        centre_x = obstacle.x + radius_x
        centre_y = obstacle.y + radius_y
        nearest_x = min(max(centre_x, box.left), box.right)
        nearest_y = min(max(centre_y, box.top), box.bottom)
        return (
            ((nearest_x - centre_x) / radius_x) ** 2
            + ((nearest_y - centre_y) / radius_y) ** 2
            <= 1
        )
    if isinstance(obstacle, Polygon):
        return _polygon_overlaps(box, obstacle.points)
    raise TypeError(f"unsupported collision obstacle: {type(obstacle).__name__}")


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


def _orientation(a, b, c):
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    return 0 if value == 0 else (1 if value > 0 else 2)


def _segments_cross(a, b, c, d):
    return (
        _orientation(a, b, c) != _orientation(a, b, d)
        and _orientation(c, d, a) != _orientation(c, d, b)
    )


def _polygon_overlaps(box, points):
    if not points:
        return False
    bounds = Aabb(
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points) - min(x for x, _ in points),
        max(y for _, y in points) - min(y for _, y in points),
    )
    if not overlaps(box, bounds):
        return False
    if any(
        box.left <= x <= box.right and box.top <= y <= box.bottom
        for x, y in points
    ):
        return True
    if any(_point_in_polygon(corner, points) for corner in box.corners):
        return True
    box_edges = tuple(zip(box.corners, box.corners[1:] + box.corners[:1], strict=True))
    polygon_edges = zip(points, points[1:] + points[:1], strict=True)
    return any(
        _segments_cross(start, end, box_start, box_end)
        for start, end in polygon_edges
        for box_start, box_end in box_edges
    )
