"""Reusable deterministic spawn queries and constraints."""

import ast
import random
from pathlib import Path

from shooter.map_definition import SpawnPoint, SpawnRegion
from shooter.spawn_selection import (
    NO_SOURCES,
    NO_VALID_POSITION,
    PlacementConstraints,
    SpawnQuery,
    SpawnSelector,
)
from shooter.world_collision import Aabb, Ellipse, Polygon


def point(name, at, **metadata):
    return SpawnPoint(name, at, **metadata)


def test_query_filters_role_tags_faction_and_actor_kind():
    sources = (
        point(
            "wanted",
            (80, 90),
            role="enemy",
            tags=frozenset(("outdoor", "north")),
            faction="horde",
            actor_kind="walker",
        ),
        point("wrong-role", (10, 10), role="survivor"),
    )
    query = SpawnQuery(
        role="enemy",
        required_tags=frozenset(("north",)),
        faction="horde",
        actor_kind="walker",
    )

    result = SpawnSelector().select(
        sources, query, PlacementConstraints(), random.Random(1)
    )

    assert result.selected is True
    assert (result.spawn_id, result.position) == ("wanted", (80, 90))


def test_untyped_enemy_lane_matches_every_requested_enemy_kind():
    source = point("shared-lane", (80, 90), role="enemy", faction="horde")

    result = SpawnSelector().select(
        (source,),
        SpawnQuery(role="enemy", faction="horde", actor_kind="runner"),
        PlacementConstraints(),
        random.Random(1),
    )

    assert (result.spawn_id, result.position) == ("shared-lane", (80, 90))


def test_region_sampling_is_reproducible_for_box_ellipse_and_polygon():
    regions = (
        SpawnRegion("box", Aabb(0, 0, 100, 100), role="enemy"),
        SpawnRegion("oval", Ellipse(0, 0, 100, 60), role="enemy"),
        SpawnRegion(
            "triangle", Polygon(((0, 0), (100, 0), (0, 100))), role="enemy"
        ),
    )
    selector = SpawnSelector()

    first = selector.select(
        regions, SpawnQuery(role="enemy"), PlacementConstraints(), random.Random(8)
    )
    second = selector.select(
        regions, SpawnQuery(role="enemy"), PlacementConstraints(), random.Random(8)
    )

    assert first == second
    assert first.selected is True


def test_all_placement_constraints_compose():
    sources = (
        point("visible", (50, 50), role="enemy"),
        point("too-near", (120, 120), role="enemy"),
        point("occupied", (240, 240), role="enemy"),
        point("colliding", (320, 320), role="enemy"),
        point("valid", (420, 420), role="enemy"),
        point("outside", (495, 495), role="enemy"),
    )
    constraints = PlacementConstraints(
        bounds=Aabb(0, 0, 500, 500),
        visible_area=Aabb(0, 0, 100, 100),
        exclude_visible=True,
        reference=(100, 100),
        minimum_distance=100,
        maximum_distance=500,
        occupied=((240, 240),),
        minimum_occupant_distance=30,
        collision=(Aabb(300, 300, 50, 50),),
        footprint=(20, 20),
    )

    result = SpawnSelector().select(
        sources, SpawnQuery(role="enemy"), constraints, random.Random(4)
    )

    assert (result.spawn_id, result.position) == ("valid", (420, 420))


def test_missing_source_and_rejected_positions_are_explicit_failures():
    selector = SpawnSelector()
    source = point("blocked", (50, 50), role="enemy")

    missing = selector.select(
        (source,), SpawnQuery(role="survivor"), PlacementConstraints(), random.Random(1)
    )
    blocked = selector.select(
        (source,),
        SpawnQuery(role="enemy"),
        PlacementConstraints(collision=(Aabb(0, 0, 100, 100),)),
        random.Random(1),
    )

    assert missing.position is None and missing.reason == NO_SOURCES
    assert blocked.position is None and blocked.reason == NO_VALID_POSITION


def test_authored_source_weights_control_lane_selection():
    sources = (
        point("disabled-lane", (50, 50), role="enemy", weight=0),
        point("active-lane", (150, 50), role="enemy", weight=3),
    )

    result = SpawnSelector().select(
        sources,
        SpawnQuery(role="enemy"),
        PlacementConstraints(),
        random.Random(1),
    )

    assert result.spawn_id == "active-lane"


def test_spawn_selection_has_no_pygame_dependency():
    source = Path("shooter/spawn_selection.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports
