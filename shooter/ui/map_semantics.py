"""Temporary debug rendering for authored map gameplay semantics.

The map definition remains authoritative data.  This module only makes that data
legible while final props and environment art are intentionally deferred.
"""

import pygame

from shooter.world_collision import Aabb, Ellipse, Polygon


INTERACTION_COLOUR = (80, 150, 255)
HARVESTABLE_COLOUR = (90, 220, 110)
CONSTRUCTION_COLOUR = (255, 180, 65)
COLLISION_COLOUR = (255, 70, 160)
PLAYABLE_AREA_COLOUR = (255, 230, 80)


class MapSemanticsRenderer:
    """Draw non-authoritative labels and outlines for map-authored objects."""

    def __init__(self):
        self.font = None

    def draw(self, surface, definition, camera=(0, 0)):
        self._ensure_font()
        for collider in definition.collision:
            if not self._visible(surface, collider, camera):
                continue
            self._draw_area(surface, collider, COLLISION_COLOUR, camera)
        for area in definition.playable_areas:
            if not self._visible(surface, area, camera):
                continue
            self._draw_area(surface, area, PLAYABLE_AREA_COLOUR, camera)
        for interaction in definition.interactions:
            if not self._visible(
                surface, interaction.position or interaction.area, camera
            ):
                continue
            self._draw_item(
                surface,
                interaction.position,
                interaction.area,
                interaction.kind.replace("_", " ").upper(),
                INTERACTION_COLOUR,
                camera,
            )
        for harvestable in definition.harvestables:
            if dict(harvestable.properties).get("debug_render") == "false":
                continue
            if not self._visible(
                surface, harvestable.position or harvestable.area, camera
            ):
                continue
            self._draw_item(
                surface,
                harvestable.position,
                harvestable.area,
                harvestable.kind.upper(),
                HARVESTABLE_COLOUR,
                camera,
            )
        for anchor in definition.construction_anchors:
            if not self._visible(surface, anchor.position or anchor.area, camera):
                continue
            self._draw_item(
                surface,
                anchor.position,
                anchor.area,
                anchor.kind.upper(),
                CONSTRUCTION_COLOUR,
                camera,
            )

    def _ensure_font(self):
        if self.font is None:
            self.font = pygame.font.Font(None, 18)

    def _draw_item(self, surface, position, area, label, colour, camera):
        if position is not None:
            centre = self._screen_point(position, camera)
            pygame.draw.circle(surface, colour, centre, 12, 2)
        elif area is not None:
            centre = self._draw_area(surface, area, colour, camera)
        else:
            return
        text = self.font.render(label, True, colour)
        surface.blit(text, (centre[0] + 14, centre[1] - text.get_height() // 2))

    @staticmethod
    def _screen_point(point, camera):
        return (round(point[0] + camera[0]), round(point[1] + camera[1]))

    def _visible(self, surface, value, camera):
        if value is None:
            return False
        if isinstance(value, tuple):
            return surface.get_rect().collidepoint(self._screen_point(value, camera))
        if isinstance(value, Aabb | Ellipse):
            return surface.get_rect().colliderect(
                value.x + camera[0],
                value.y + camera[1],
                value.width,
                value.height,
            )
        if isinstance(value, Polygon):
            points = tuple(self._screen_point(point, camera) for point in value.points)
            left = min(point[0] for point in points)
            right = max(point[0] for point in points)
            top = min(point[1] for point in points)
            bottom = max(point[1] for point in points)
            return surface.get_rect().colliderect(
                pygame.Rect(left, top, right - left, bottom - top)
            )
        raise TypeError(f"unsupported map semantic area: {type(value).__name__}")

    def _draw_area(self, surface, area, colour, camera):
        if isinstance(area, Aabb):
            rect = pygame.Rect(
                round(area.x + camera[0]),
                round(area.y + camera[1]),
                round(area.width),
                round(area.height),
            )
            pygame.draw.rect(surface, colour, rect, 2)
            return rect.center
        if isinstance(area, Ellipse):
            rect = pygame.Rect(
                round(area.x + camera[0]),
                round(area.y + camera[1]),
                round(area.width),
                round(area.height),
            )
            pygame.draw.ellipse(surface, colour, rect, 2)
            return rect.center
        if isinstance(area, Polygon):
            points = tuple(self._screen_point(point, camera) for point in area.points)
            pygame.draw.polygon(surface, colour, points, 2)
            return (
                round(sum(point[0] for point in points) / len(points)),
                round(sum(point[1] for point in points) / len(points)),
            )
        raise TypeError(f"unsupported map semantic area: {type(area).__name__}")
