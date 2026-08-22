"""The first non-Survival mode exercises the neutral Match contract."""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from shooter.domain_events import DamageApplied
from shooter.map_definition import MapDefinition, SpawnPoint, SpawnRegion
from shooter.match import DISPOSED, Match
from shooter.match_configuration import (
    SANDBOX,
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    default_mode_catalog,
)
from shooter.modes.sandbox import (
    COMPLETE,
    AttackActor,
    MoveActor,
    SandboxMode,
    SandboxStatus,
)
from shooter.spatial import Transform
from shooter.world_collision import Aabb


def resolved_sandbox():
    definition = MapDefinition(
        "arena",
        "Arena",
        "unused.tmx",
        (800, 600),
        capabilities=frozenset(("bounds",)),
    )
    return MatchConfigurationResolver(
        default_mode_catalog(), MapCatalog((definition,))
    ).resolve(MatchConfiguration(SANDBOX, "arena", 19))


def test_default_catalog_resolves_sandbox_without_survival_map_features():
    resolved = resolved_sandbox()

    assert resolved.compatible is True
    assert resolved.mode.mode_id == SANDBOX
    assert resolved.mode.hostile_factions == (("red", "blue"),)


def test_sandbox_runs_the_match_lifecycle_and_reports_frozen_status():
    match = Match(resolved_sandbox())
    mode = SandboxMode(duration_seconds=1.0)
    match.start(mode)

    match.advance(0.4, ("ignored-by-policy",))
    first = match.snapshot()
    match.advance(0.6)

    assert mode.started is True
    assert first.mode_status == SandboxStatus(0.4, 1)
    assert first.result is None
    assert match.snapshot().mode_status == SandboxStatus(1.0, 2, COMPLETE)
    assert match.result == COMPLETE
    with pytest.raises(FrozenInstanceError):
        first.mode_status.elapsed = 10

    match.dispose()
    assert match.state == DISPOSED
    assert mode.disposed is True


def test_sandbox_can_run_without_a_completion_limit():
    match = Match(resolved_sandbox())
    mode = SandboxMode()
    match.start(mode)
    match.advance(60.0)

    assert match.result is None
    assert match.mode_status == SandboxStatus(60.0, 1)


def test_sandbox_rejects_invalid_time():
    with pytest.raises(ValueError, match="duration_seconds"):
        SandboxMode(-1)

    match = Match(resolved_sandbox())
    match.start(SandboxMode())
    with pytest.raises(ValueError, match="dt"):
        match.advance(-0.1)


def test_sandbox_package_has_no_pygame_ui_or_survival_imports():
    forbidden = ("pygame", "shooter.ui", "shooter.modes.zombie_survival")
    for filename in (
        "shooter/modes/sandbox/__init__.py",
        "shooter/modes/sandbox/mode.py",
    ):
        imports = set()
        for node in ast.walk(ast.parse(Path(filename).read_text())):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        assert not any(
            dependency == prefix or dependency.startswith(f"{prefix}.")
            for dependency in imports
            for prefix in forbidden
        ), filename


def sandbox_spawns():
    return (
        SpawnPoint(
            "red-start",
            (100, 200),
            role="player",
            faction="red",
            actor_kind="soldier",
        ),
        SpawnPoint(
            "blue-start",
            (700, 400),
            role="player",
            faction="blue",
            actor_kind="soldier",
        ),
    )


def test_sandbox_reuses_spawn_registry_spatial_combat_and_faction_stores():
    match = Match(resolved_sandbox())
    mode = SandboxMode(spawn_sources=sandbox_spawns())
    match.start(mode)
    red = mode.actor_ids["red"]
    blue = mode.actor_ids["blue"]
    match.events.drain()

    assert mode.spawn_results[0].complete is True
    assert mode.spawn_results[1].complete is True
    assert match.entities.ids("actor") == (red, blue)
    assert match.spatial.get(red).transform == Transform(100, 200)
    assert match.spatial.get(blue).transform == Transform(700, 400)
    assert match.combat.get(red).health == 100
    assert match.factions.faction_of(blue) == "blue"


def test_sandbox_moves_and_applies_attributed_hostile_damage_headlessly():
    match = Match(resolved_sandbox())
    mode = SandboxMode(spawn_sources=sandbox_spawns())
    match.start(mode)
    red = mode.actor_ids["red"]
    blue = mode.actor_ids["blue"]
    match.events.drain()

    match.advance(
        0.5,
        (
            MoveActor(red, (1, 0)),
            AttackActor(red, blue, 35),
        ),
    )
    snapshot = match.snapshot()

    assert snapshot.entity(red).position == (180, 200)
    assert snapshot.entity(blue).vitality.health == 65
    assert snapshot.entity(red).faction == "red"
    assert snapshot.mode_status.actors_alive == 2
    assert match.events.drain() == (
        DamageApplied(red, blue, 35, red, None, "sandbox", 1, 0.0, 35),
    )


def test_sandbox_region_spawning_is_seeded_by_match_configuration():
    sources = (
        SpawnRegion(
            "red-zone",
            Aabb(50, 50, 200, 200),
            role="player",
            faction="red",
            actor_kind="soldier",
        ),
        SpawnRegion(
            "blue-zone",
            Aabb(500, 300, 200, 200),
            role="player",
            faction="blue",
            actor_kind="soldier",
        ),
    )
    positions = []
    for _ in range(2):
        match = Match(resolved_sandbox())
        mode = SandboxMode(spawn_sources=sources)
        match.start(mode)
        positions.append(
            tuple(
                match.spatial.get(mode.actor_ids[faction]).transform
                for faction in ("red", "blue")
            )
        )

    assert positions[0] == positions[1]
