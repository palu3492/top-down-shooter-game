"""Data-driven modular environment used by the fixed-screen 2.5D demo.

The module deliberately has no dependency on ``depth_demo``.  A scene can use
``EnvironmentMap.footprints`` for movement/navigation and merge
``depth_entries()`` with its actors before drawing them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pygame

ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_ROOT = ROOT / "Assets" / "Demo2_5D" / "environment"
DEFAULT_LAYOUT = Path(__file__).with_name("depth_demo_layout.json")


@dataclass(frozen=True)
class PropDefinition:
    asset: str
    size: tuple[int, int]
    footprint: tuple[int, int]
    anchor: tuple[float, float] = (0.5, 1.0)
    tall: bool = False
    color: tuple[int, int, int] = (83, 76, 49)


PROP_DEFINITIONS: dict[str, PropDefinition] = {
    "tree_1": PropDefinition(
        "props/tree_a.png", (190, 197), (38, 28), tall=True, color=(48, 68, 30)
    ),
    "tree_2": PropDefinition(
        "props/tree_b.png", (178, 208), (38, 28), tall=True, color=(45, 65, 27)
    ),
    "tree_3": PropDefinition(
        "props/tree_c.png", (195, 185), (40, 28), tall=True, color=(54, 72, 32)
    ),
    "bush_1": PropDefinition(
        "props/bush_a.png", (105, 119), (64, 32), tall=True, color=(45, 76, 31)
    ),
    "bush_2": PropDefinition(
        "props/bush_b.png", (115, 116), (70, 32), tall=True, color=(51, 83, 34)
    ),
    "bush_3": PropDefinition(
        "props/bush_c.png", (123, 116), (72, 34), tall=True, color=(41, 71, 28)
    ),
    "bush_4": PropDefinition(
        "props/bush_d.png", (100, 122), (62, 34), tall=True, color=(56, 87, 36)
    ),
    "grass_1": PropDefinition(
        "props/grass_a.png", (52, 64), (1, 1), color=(59, 78, 32)
    ),
    "grass_2": PropDefinition(
        "props/grass_b.png", (50, 56), (1, 1), color=(55, 73, 30)
    ),
    "grass_3": PropDefinition(
        "props/grass_c.png", (56, 58), (1, 1), color=(64, 80, 34)
    ),
    "dead_shrub_1": PropDefinition(
        "props/dead_shrub_a.png", (56, 52), (24, 14), color=(73, 61, 41)
    ),
    "dead_shrub_2": PropDefinition(
        "props/dead_shrub_b.png", (48, 53), (22, 13), color=(69, 58, 39)
    ),
    "fence_straight_1": PropDefinition(
        "props/fence_straight_a.png", (150, 104), (130, 20)
    ),
    "fence_straight_2": PropDefinition(
        "props/fence_straight_b.png", (145, 102), (126, 20)
    ),
    "fence_broken": PropDefinition("props/fence_broken.png", (145, 94), (122, 18)),
    "fence_corner": PropDefinition("props/fence_corner.png", (148, 107), (110, 44)),
    "barricade": PropDefinition("props/barricade.png", (142, 86), (118, 22)),
    "vehicle_pickup": PropDefinition(
        "props/vehicle_pickup.png", (172, 196), (104, 66), color=(67, 61, 49)
    ),
    "vehicle_sedan": PropDefinition(
        "props/vehicle_sedan.png", (170, 146), (110, 54), color=(67, 61, 49)
    ),
    "barrels_1": PropDefinition("props/barrels_a.png", (88, 80), (58, 34)),
    "barrels_2": PropDefinition("props/barrels_b.png", (90, 79), (60, 34)),
    "crates_1": PropDefinition("props/crates_a.png", (102, 86), (72, 34)),
    "crates_2": PropDefinition("props/crates_b.png", (100, 94), (70, 36)),
    "hay_bales": PropDefinition("props/hay_bales.png", (125, 80), (92, 38)),
    "wagon": PropDefinition("props/wagon.png", (145, 138), (100, 48)),
    "wagon_wheel": PropDefinition("props/wagon_wheel.png", (74, 72), (48, 18)),
    "rocks_large": PropDefinition("props/rocks_large.png", (108, 90), (76, 43)),
    "rocks_small": PropDefinition("props/rocks_small.png", (66, 56), (42, 24)),
    "log": PropDefinition("props/log.png", (118, 83), (94, 28)),
    "stump": PropDefinition("props/stump.png", (78, 72), (47, 28)),
    "boards": PropDefinition("props/boards.png", (94, 54), (66, 20)),
}

DECAL_SIZES = {
    "puddle": (115, 81),
    "tire_tracks": (122, 103),
    "trampled_grass": (110, 89),
    "dirt_patch": (118, 90),
    "pebbles": (78, 55),
}


@dataclass
class DepthEntry:
    ground_y: float
    prop: EnvironmentProp

    def draw(
        self, target: pygame.Surface, player_position: pygame.Vector2 | None = None
    ) -> None:
        self.prop.draw(target, player_position)


@dataclass
class EnvironmentProp:
    kind: str
    position: pygame.Vector2
    definition: PropDefinition
    image: pygame.Surface
    footprint: pygame.Rect

    @property
    def ground_y(self) -> float:
        return self.position.y

    @property
    def image_rect(self) -> pygame.Rect:
        anchor_x, anchor_y = self.definition.anchor
        return self.image.get_rect(
            topleft=(
                round(self.position.x - self.image.width * anchor_x),
                round(self.position.y - self.image.height * anchor_y),
            )
        )

    def obscures(self, player_position: pygame.Vector2) -> bool:
        if not self.definition.tall or player_position.y >= self.ground_y + 10:
            return False
        actor_probe = pygame.Rect(
            round(player_position.x - 18), round(player_position.y - 70), 36, 76
        )
        return self.image_rect.colliderect(actor_probe)

    def draw(
        self, target: pygame.Surface, player_position: pygame.Vector2 | None = None
    ) -> None:
        image = self.image
        if player_position is not None and self.obscures(player_position):
            image = image.copy()
            image.set_alpha(115)
        target.blit(image, self.image_rect)


def _fallback_prop(definition: PropDefinition) -> pygame.Surface:
    surface = pygame.Surface(definition.size, pygame.SRCALPHA)
    w, h = definition.size
    pygame.draw.ellipse(
        surface, (0, 0, 0, 55), (w * 0.14, h * 0.86, w * 0.72, h * 0.11)
    )
    pygame.draw.ellipse(surface, definition.color, (4, 5, w - 8, h - 14))
    highlight = tuple(min(channel + 25, 255) for channel in definition.color)
    pygame.draw.ellipse(surface, highlight, (w * 0.2, h * 0.1, w * 0.55, h * 0.45))
    return surface


def _load_image(
    path: Path, size: tuple[int, int], fallback: pygame.Surface
) -> pygame.Surface:
    if path.is_file():
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(image, size)
        except pygame.error:
            pass
    return fallback


def _fallback_decal(kind: str, size: tuple[int, int]) -> pygame.Surface:
    surface = pygame.Surface(size, pygame.SRCALPHA)
    color = (81, 67, 42, 105) if kind != "trampled_grass" else (53, 65, 31, 115)
    pygame.draw.ellipse(surface, color, surface.get_rect().inflate(-4, -8))
    return surface


class EnvironmentMap:
    """Loaded arena decoration, obstacles, and reusable rendering hooks."""

    def __init__(self, layout_path: Path = DEFAULT_LAYOUT):
        with layout_path.open(encoding="utf-8") as handle:
            data: dict[str, Any] = json.load(handle)
        self.size = tuple(data["size"])
        self.background = tuple(data.get("background", (58, 69, 34)))
        self.decals = self._load_decals(data["decals"])
        self.props = self._load_props(data["props"])

    def _load_props(self, placements: list[dict[str, Any]]) -> list[EnvironmentProp]:
        cache: dict[str, pygame.Surface] = {}
        props = []
        for placement in placements:
            kind = placement["kind"]
            definition = PROP_DEFINITIONS[kind]
            if kind not in cache:
                cache[kind] = _load_image(
                    ENVIRONMENT_ROOT / definition.asset,
                    definition.size,
                    _fallback_prop(definition),
                )
            position = pygame.Vector2(placement["position"])
            footprint = pygame.Rect((0, 0), definition.footprint)
            footprint.midbottom = round(position.x), round(position.y)
            props.append(
                EnvironmentProp(kind, position, definition, cache[kind], footprint)
            )
        return props

    def _load_decals(
        self, placements: list[dict[str, Any]]
    ) -> list[tuple[pygame.Surface, pygame.Rect]]:
        cache: dict[str, pygame.Surface] = {}
        decals = []
        for placement in placements:
            kind = placement["kind"]
            size = DECAL_SIZES[kind]
            if kind not in cache:
                cache[kind] = _load_image(
                    ENVIRONMENT_ROOT / "decals" / f"{kind}.png",
                    size,
                    _fallback_decal(kind, size),
                )
                cache[kind].set_alpha(placement.get("alpha", 190))
            image = cache[kind]
            rect = image.get_rect(center=placement["position"])
            decals.append((image, rect))
        return decals

    @property
    def footprints(self) -> list[pygame.Rect]:
        return [prop.footprint for prop in self.props]

    def blocked(self, position: pygame.Vector2, radius: int) -> bool:
        probe = pygame.Rect(0, 0, radius * 2, radius * 2)
        probe.center = round(position.x), round(position.y)
        return any(probe.colliderect(footprint) for footprint in self.footprints)

    def draw_ground(self, target: pygame.Surface) -> None:
        target.fill(self.background)
        self.draw_decals(target)

    def draw_decals(self, target: pygame.Surface) -> None:
        """Layer details over an existing painted ground without replacing it."""
        for image, rect in self.decals:
            target.blit(image, rect)

    def depth_entries(self) -> list[DepthEntry]:
        return [DepthEntry(prop.ground_y, prop) for prop in self.props]

    def draw_props(
        self, target: pygame.Surface, player_position: pygame.Vector2 | None = None
    ) -> None:
        for entry in sorted(self.depth_entries(), key=lambda item: item.ground_y):
            entry.draw(target, player_position)
