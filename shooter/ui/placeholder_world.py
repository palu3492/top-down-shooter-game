"""Debug-shape rendering from immutable entity snapshots."""

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class ShapeBinding:
    shape: str
    colour: tuple[int, int, int]
    size: int
    outline: int = 0


PLAYER = ShapeBinding("circle", (40, 210, 255), 22)
ENEMY = ShapeBinding("circle", (225, 65, 65), 24)
BALLISTIC = ShapeBinding("circle", (255, 235, 70), 4)
MELEE = ShapeBinding("circle", (245, 245, 245), 30, 3)
GRENADE = ShapeBinding("circle", (255, 145, 35), 8)
EXPLOSIVE = ShapeBinding("circle", (255, 95, 25), 38, 4)
STUN = ShapeBinding("circle", (120, 190, 255), 34, 4)
POWERUP = ShapeBinding("diamond", (210, 80, 255), 12)
PICKUP = ShapeBinding("box", (80, 220, 110), 16)
INTERACTABLE = ShapeBinding("box", (80, 150, 255), 28, 3)
NEUTRAL = ShapeBinding("box", (180, 180, 180), 14, 2)


def binding_for(entity):
    tags = entity.tags
    if "player" in tags:
        return PLAYER
    if "enemy" in tags:
        return ENEMY
    if "ballistic" in tags:
        return BALLISTIC
    if "melee" in tags:
        return MELEE
    if "grenade" in tags:
        return GRENADE
    if "explosive" in tags:
        return EXPLOSIVE
    if "stun" in tags:
        return STUN
    if "powerup" in tags:
        return POWERUP
    if "pickup" in tags:
        return PICKUP
    if "interactable" in tags:
        return INTERACTABLE
    return NEUTRAL


class PlaceholderWorldRenderer:
    def draw(self, surface, snapshot, camera=(0, 0)):
        for entity in snapshot.entities:
            if entity.position is None:
                continue
            binding = binding_for(entity)
            centre = (
                round(entity.position[0] + camera[0]),
                round(entity.position[1] + camera[1]),
            )
            self._shape(surface, centre, binding)
            if "actor" in entity.tags and entity.vitality is not None:
                self._health(surface, centre, binding.size, entity.vitality)
        self._ballistic_traces(surface, snapshot.mode_status, camera)

    @staticmethod
    def _ballistic_traces(surface, status, camera):
        for trace in getattr(status, "ballistic_traces", ()):
            travelled = trace.speed * trace.elapsed
            x = trace.origin[0] + trace.direction[0] * travelled + camera[0]
            y = trace.origin[1] + trace.direction[1] * travelled + camera[1]
            pygame.draw.circle(surface, (0, 0, 0), (round(x), round(y)), 3)

    @staticmethod
    def _shape(surface, centre, binding):
        if binding.shape == "circle":
            pygame.draw.circle(
                surface,
                binding.colour,
                centre,
                binding.size,
                binding.outline,
            )
        elif binding.shape == "diamond":
            x, y = centre
            size = binding.size
            pygame.draw.polygon(
                surface,
                binding.colour,
                ((x, y - size), (x + size, y), (x, y + size), (x - size, y)),
                binding.outline,
            )
        else:
            size = binding.size
            rect = pygame.Rect(0, 0, size * 2, size * 2)
            rect.center = centre
            pygame.draw.rect(surface, binding.colour, rect, binding.outline)

    @staticmethod
    def _health(surface, centre, radius, vitality):
        width = radius * 2
        background = pygame.Rect(centre[0] - radius, centre[1] - radius - 10, width, 5)
        pygame.draw.rect(surface, (45, 45, 45), background)
        remaining = (
            0 if vitality.max_health <= 0 else vitality.health / vitality.max_health
        )
        foreground = background.copy()
        foreground.width = round(width * remaining)
        pygame.draw.rect(surface, (70, 225, 90), foreground)
