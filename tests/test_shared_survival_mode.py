"""The first Survival slice runs on neutral Match actors and stores."""

import ast
import math
from pathlib import Path

from shooter.domain_events import DamageApplied, EntityKilled
from shooter.map_definition import MapDefinition, SpawnPoint, SpawnRegion
from shooter.match import Match
from shooter.match_configuration import (
    ZOMBIE_SURVIVAL,
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    default_mode_catalog,
)
from shooter.modes.zombie_survival import DamageEnemy, MoveSurvivor, SurvivalMode
from shooter.world_collision import Aabb


def resolved():
    definition = MapDefinition(
        "arena",
        "Arena",
        "unused.tmx",
        (1000, 800),
        capabilities=frozenset(("bounds",)),
    )
    return MatchConfigurationResolver(
        default_mode_catalog(), MapCatalog((definition,))
    ).resolve(MatchConfiguration(ZOMBIE_SURVIVAL, "arena", 91))


def sources():
    return (
        SpawnPoint(
            "survivor",
            (500, 400),
            role="player",
            faction="survivors",
            actor_kind="soldier",
        ),
        SpawnRegion(
            "horde",
            Aabb(100, 100, 220, 500),
            role="enemy",
            faction="horde",
            actor_kind="walker",
        ),
    )


def test_survival_spawns_player_and_initial_horde_into_match_stores():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=5)
    match.start(mode)
    snapshot = match.snapshot()

    assert mode.player_id is not None
    assert len(mode.enemy_ids) == 5
    assert len(snapshot.entities) == 6
    assert snapshot.entity(mode.player_id).tags >= {"actor", "player"}
    assert all(
        snapshot.entity(enemy).tags >= {"actor", "enemy"}
        for enemy in mode.enemy_ids
    )
    assert snapshot.mode_status.enemies_remaining == 5


def test_survivor_and_enemies_move_in_authoritative_world_space():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    enemy = mode.enemy_ids[0]
    player_before = match.spatial.get(mode.player_id).transform
    enemy_before = match.spatial.get(enemy).transform
    match.advance(0.1, (MoveSurvivor((1, 0)),))
    player_after = match.spatial.get(mode.player_id).transform
    enemy_after = match.spatial.get(enemy).transform

    assert player_after.x > player_before.x
    assert math.dist(
        (player_after.x, player_after.y), (enemy_after.x, enemy_after.y)
    ) < math.dist(
        (player_after.x, player_after.y), (enemy_before.x, enemy_before.y)
    )


def test_attributed_enemy_death_is_visible_in_snapshot_and_status():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    enemy = mode.enemy_ids[0]
    match.events.drain()

    match.advance(0.0, (DamageEnemy(enemy, 100),))
    snapshot = match.snapshot()

    assert snapshot.entity(enemy).vitality.alive is False
    assert snapshot.mode_status.enemies_remaining == 0
    assert match.events.drain() == (
        DamageApplied(
            mode.player_id,
            enemy,
            100,
            mode.player_id,
            None,
            "survivor_attack",
            1,
            0.0,
            100,
        ),
        EntityKilled(enemy, mode.player_id, mode.player_id, None, "survivor_attack", 1),
    )


def test_new_survival_mode_has_no_pygame_sprite_or_session_dependency():
    imports = set()
    for node in ast.walk(
        ast.parse(Path("shooter/modes/zombie_survival/mode.py").read_text())
    ):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "pygame" not in imports
    assert "shooter.session" not in imports
    assert not any(name.startswith("shooter.entities") for name in imports)
