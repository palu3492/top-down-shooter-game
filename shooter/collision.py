"""Collision geometry authored as objects in a Tiled map."""

from dataclasses import dataclass
from xml.etree import ElementTree

import pygame

from shooter.assets import asset_path


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


@dataclass(frozen=True)
class PolygonObstacle:
    points: tuple[tuple[float, float], ...]

    def colliderect(self, rect):
        bounds = pygame.Rect(
            min(x for x, _ in self.points),
            min(y for _, y in self.points),
            max(x for x, _ in self.points) - min(x for x, _ in self.points),
            max(y for _, y in self.points) - min(y for _, y in self.points),
        )
        if not bounds.colliderect(rect):
            return False
        if any(rect.collidepoint(point) for point in self.points):
            return True
        corners = (rect.topleft, rect.topright, rect.bottomright, rect.bottomleft)
        if any(_point_in_polygon(point, self.points) for point in corners):
            return True
        return any(
            rect.clipline(start, end)
            for start, end in zip(
                self.points, self.points[1:] + self.points[:1], strict=True
            )
        )

    def draw(self, surface, colour, camera):
        pygame.draw.polygon(
            surface,
            colour,
            [(x + camera[0], y + camera[1]) for x, y in self.points],
            2,
        )


@dataclass(frozen=True)
class EllipseObstacle:
    x: float
    y: float
    width: float
    height: float

    def colliderect(self, rect):
        radius_x = self.width / 2
        radius_y = self.height / 2
        if radius_x <= 0 or radius_y <= 0:
            return False
        centre_x = self.x + radius_x
        centre_y = self.y + radius_y
        nearest_x = min(max(centre_x, rect.left), rect.right)
        nearest_y = min(max(centre_y, rect.top), rect.bottom)
        return (
            ((nearest_x - centre_x) / radius_x) ** 2
            + ((nearest_y - centre_y) / radius_y) ** 2
            <= 1
        )

    def draw(self, surface, colour, camera):
        pygame.draw.ellipse(
            surface,
            colour,
            pygame.Rect(
                round(self.x + camera[0]),
                round(self.y + camera[1]),
                round(self.width),
                round(self.height),
            ),
            2,
        )


def load_obstacles(relative):
    """Read collision geometry from a TMX semantic object layer.

    ``Collision`` is the current map contract. ``Obstacles`` remains accepted
    while older authored maps are migrated.
    """
    root = ElementTree.parse(asset_path(relative)).getroot()
    layer = next(
        (
            node
            for node in root.findall("objectgroup")
            if node.get("name") in {"Collision", "Obstacles"}
        ),
        None,
    )
    if layer is None:
        return []

    offset_x = float(layer.get("offsetx", 0))
    offset_y = float(layer.get("offsety", 0))
    obstacles = []
    for obj in layer.findall("object"):
        x = float(obj.get("x", 0)) + offset_x
        y = float(obj.get("y", 0)) + offset_y
        ellipse = obj.find("ellipse")
        polygon = obj.find("polygon")
        if ellipse is not None:
            obstacles.append(
                EllipseObstacle(
                    x, y, float(obj.get("width", 0)), float(obj.get("height", 0))
                )
            )
        elif polygon is not None:
            points = tuple(
                (x + float(pair.split(",")[0]), y + float(pair.split(",")[1]))
                for pair in polygon.get("points", "").split()
            )
            if len(points) >= 3:
                obstacles.append(PolygonObstacle(points))
    return obstacles
