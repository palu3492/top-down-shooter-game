"""Temporary map-semantic debug markers are presentation only."""

import pygame

from shooter.map_definition import (
    MapConstructionAnchor,
    MapDefinition,
    MapHarvestable,
    MapInteraction,
)
from shooter.ui.map_semantics import (
    CONSTRUCTION_COLOUR,
    COLLISION_COLOUR,
    HARVESTABLE_COLOUR,
    INTERACTION_COLOUR,
    MapSemanticsRenderer,
)
from shooter.world_collision import Aabb


def test_renderer_outlines_authored_map_semantics_at_world_positions(display):
    definition = MapDefinition(
        "test",
        "Test",
        "unused.tmx",
        (400, 300),
        collision=(Aabb(20, 20, 20, 20),),
        interactions=(MapInteraction("station", "weapon_station", position=(50, 60)),),
        harvestables=(
            MapHarvestable("tree", "tree", area=Aabb(100, 100, 40, 50)),
        ),
        construction_anchors=(
            MapConstructionAnchor("gate", "barricade", area=Aabb(200, 160, 60, 20)),
        ),
    )
    surface = pygame.Surface((400, 300))

    MapSemanticsRenderer().draw(surface, definition)

    assert surface.get_at((50, 48))[:3] == INTERACTION_COLOUR
    assert surface.get_at((20, 20))[:3] == COLLISION_COLOUR
    assert surface.get_at((100, 100))[:3] == HARVESTABLE_COLOUR
    assert surface.get_at((200, 160))[:3] == CONSTRUCTION_COLOUR


def test_renderer_applies_camera_offset_to_authored_map_semantics(display):
    definition = MapDefinition(
        "test",
        "Test",
        "unused.tmx",
        (400, 300),
        harvestables=(MapHarvestable("truck", "vehicle", area=Aabb(100, 100, 40, 20)),),
    )
    surface = pygame.Surface((400, 300))

    MapSemanticsRenderer().draw(surface, definition, camera=(-20, 30))

    assert surface.get_at((80, 130))[:3] == HARVESTABLE_COLOUR
