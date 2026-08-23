"""Map interactions are queried without Tiled or presentation dependencies."""

import ast
from pathlib import Path

import pytest

from shooter.interaction_query import nearest_interaction
from shooter.map_definition import MapInteraction
from shooter.world_collision import Aabb


def test_nearest_interaction_filters_kind_tags_and_range():
    interactions = (
        MapInteraction("far", "weapon_station", position=(100, 0)),
        MapInteraction(
            "near",
            "weapon_station",
            position=(20, 0),
            tags=frozenset(("survival",)),
        ),
        MapInteraction("ammo", "ammo_station", position=(5, 0)),
    )

    found = nearest_interaction(
        interactions,
        (0, 0),
        30,
        kind="weapon_station",
        required_tags=("survival",),
    )

    assert found.interaction_id == "near"


def test_region_distance_and_id_tie_breaking_are_deterministic():
    interactions = (
        MapInteraction("bravo", "door", area=Aabb(20, 20, 10, 10)),
        MapInteraction("alpha", "door", area=Aabb(20, 20, 10, 10)),
    )

    assert nearest_interaction(interactions, (25, 25), 0).interaction_id == "alpha"
    assert nearest_interaction(interactions, (0, 0), 10) is None


def test_query_rejects_negative_range_and_has_no_pygame_dependency():
    with pytest.raises(ValueError):
        nearest_interaction((), (0, 0), -1)

    imports = set()
    for node in ast.walk(ast.parse(Path("shooter/interaction_query.py").read_text())):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert "pygame" not in imports
