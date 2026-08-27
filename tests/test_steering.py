"""Reusable pursuit is deterministic and obstacle-aware."""

import ast
from pathlib import Path
from types import SimpleNamespace

from shooter.map_definition import MapDefinition
from shooter.match import Match
from shooter.match_configuration import (
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.spatial import Box, Transform
from shooter.steering import nearby_occupants, pursue_match_actor
from shooter.world_collision import Aabb


def owner(collision=()):
    definition = MapDefinition(
        "arena", "Arena", "unused.tmx", (400, 300), collision=collision
    )
    resolved = MatchConfigurationResolver(
        ModeCatalog((ModeDescriptor("test", "Test", ""),)),
        MapCatalog((definition,)),
    ).resolve(MatchConfiguration("test", "arena", 1))
    return Match(resolved)


def attach(match, position, speed=80):
    actor = SimpleNamespace(movement_speed=speed, collision_size=(20, 20))
    actor_id = match.entities.register(actor, ("actor",))
    match.spatial.attach(actor_id, Transform(*position), Box(20, 20))
    return actor_id


def test_pursuit_uses_direct_shared_movement_in_open_space():
    match = owner()
    mover = attach(match, (50, 50))
    target = attach(match, (150, 50), speed=0)

    pursue_match_actor(match, mover, target, 0.5)

    assert match.spatial.get(mover).transform == Transform(90, 50)


def test_blocked_pursuit_deterministically_steers_around_a_wall():
    match = owner((Aabb(190, 100, 20, 100),))
    mover = attach(match, (180, 150))
    target = attach(match, (260, 150), speed=0)

    first = pursue_match_actor(match, mover, target, 0.1).transform
    for _ in range(30):
        pursue_match_actor(match, mover, target, 0.1)
    final = match.spatial.get(mover).transform

    assert first.y > 150
    assert final.x > 210
    assert final.x > first.x


def test_nearby_occupants_bounds_dense_crowd_collision_work():
    match = owner()
    actor_ids = tuple(attach(match, (50 + index, 50)) for index in range(20))

    occupants = nearby_occupants(match, actor_ids, limit=4)

    assert len(occupants[actor_ids[10]]) == 4
    assert actor_ids[9] in occupants[actor_ids[10]]
    assert actor_ids[10] not in occupants[actor_ids[10]]


def test_steering_has_no_pygame_or_mode_dependency():
    imports = set()
    for node in ast.walk(ast.parse(Path("shooter/steering.py").read_text())):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(
        name == "pygame" or name.startswith("shooter.modes") for name in imports
    )
