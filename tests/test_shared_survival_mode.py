"""The first Survival slice runs on neutral Match actors and stores."""

import ast
import math
from pathlib import Path

from shooter import config
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
from shooter.modes.zombie_survival import (
    FireSurvivorWeapon,
    MoveSurvivor,
    ReloadSurvivorWeapon,
    SurvivalMode,
)
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


def aim_at(match, mode, target_id):
    player = match.spatial.get(mode.player_id).transform
    target = match.spatial.get(target_id).transform
    return target.x - player.x, target.y - player.y


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
    match.combat.deplete(enemy, 80)
    match.events.drain()

    match.advance(0.0, (FireSurvivorWeapon(aim_at(match, mode, enemy)),))
    snapshot = match.snapshot()

    assert snapshot.entity(enemy).vitality.alive is False
    assert snapshot.mode_status.enemies_remaining == 0
    assert snapshot.mode_status.cash == config.KILL_REWARD
    assert match.events.drain() == (
        DamageApplied(
            mode.player_id,
            enemy,
            20,
            mode.player_id,
            "survivor_rifle",
            "ballistic",
            1,
            0.0,
            20,
        ),
        EntityKilled(
            enemy,
            mode.player_id,
            mode.player_id,
            "survivor_rifle",
            "ballistic",
            1,
        ),
    )


def test_cleared_wave_enters_preparation_then_spawns_an_escalated_wave():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1, preparation_seconds=2.0)
    match.start(mode)
    match.combat.deplete(mode.enemy_ids[0], 80)
    match.advance(
        0.0,
        (FireSurvivorWeapon(aim_at(match, mode, mode.enemy_ids[0])),),
    )

    assert match.mode_status.phase == "preparation"
    assert match.mode_status.wave == 1
    assert match.mode_status.preparation_remaining == 2.0

    match.advance(1.25)
    assert match.mode_status.preparation_remaining == 0.75
    match.advance(0.75)

    assert match.mode_status.phase == "combat"
    assert match.mode_status.wave == 2
    assert match.mode_status.enemies_remaining == 2
    assert match.mode_status.cash == config.KILL_REWARD
    assert len(mode.enemy_ids) == 3


def test_survival_awards_each_eligible_enemy_kill_exactly_once():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    enemy = mode.enemy_ids[0]
    aim = aim_at(match, mode, enemy)
    match.combat.deplete(enemy, 80)

    match.advance(0.0, (FireSurvivorWeapon(aim),))
    match.advance(1 / 6, (FireSurvivorWeapon(aim),))

    assert mode.cash.balance == config.KILL_REWARD
    assert match.mode_status.cash == config.KILL_REWARD


def test_survivor_rifle_ammo_cooldown_reload_and_snapshot_are_authoritative():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    enemy = mode.enemy_ids[0]

    aim = aim_at(match, mode, enemy)
    match.advance(0.0, (FireSurvivorWeapon(aim),))
    match.advance(0.0, (FireSurvivorWeapon(aim),))
    weapon = match.snapshot().entity(mode.player_id).weapons[0]
    assert weapon.loaded == 59
    assert weapon.ready is False

    match.advance(1 / 6, (FireSurvivorWeapon(aim_at(match, mode, enemy)),))
    assert match.snapshot().entity(mode.player_id).weapons[0].loaded == 58
    match.advance(0.0, (ReloadSurvivorWeapon(),))
    weapon = match.snapshot().entity(mode.player_id).weapons[0]
    assert (weapon.loaded, weapon.reserve) == (60, 118)
    assert weapon.status == "reload"

    match.advance(config.RELOAD_SECONDS)
    assert match.snapshot().entity(mode.player_id).weapons[0].ready is True


def test_weapon_ray_hits_nearest_enemy_and_a_miss_still_spends_ammunition():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=2)
    match.start(mode)
    player = match.spatial.get(mode.player_id).transform
    near, far = mode.enemy_ids
    match.spatial.move_to(near, player.x + 100, player.y)
    match.spatial.move_to(far, player.x + 200, player.y)

    match.advance(0.0, (FireSurvivorWeapon((1, 0)),))

    assert match.combat.get(near).health == 80
    assert match.combat.get(far).health == 100
    match.advance(1 / 6, (FireSurvivorWeapon((0, -1)),))
    assert match.snapshot().entity(mode.player_id).weapons[0].loaded == 58
    assert match.combat.get(near).health == 80
    assert match.combat.get(far).health == 100


def test_overlapping_enemy_deals_attributed_contact_damage_over_time():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    enemy = mode.enemy_ids[0]
    player_position = match.spatial.get(mode.player_id).transform
    match.spatial.move_to(enemy, player_position.x, player_position.y)
    match.events.drain()

    match.advance(0.5)

    assert match.combat.get(mode.player_id).health == 97
    event = match.events.drain()[0]
    assert event == DamageApplied(
        enemy,
        mode.player_id,
        3,
        enemy,
        None,
        "contact",
        1,
        0.0,
        3,
    )


def test_lethal_contact_damage_ends_survival_and_stops_progression():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1, preparation_seconds=0)
    match.start(mode)
    enemy = mode.enemy_ids[0]
    player_position = match.spatial.get(mode.player_id).transform
    match.spatial.move_to(enemy, player_position.x, player_position.y)

    match.advance(20)

    assert match.result == "LOST"
    assert match.mode_status.outcome == "LOST"
    assert match.mode_status.wave == 1
    before = match.spatial.get(enemy).transform
    match.advance(1)
    assert match.spatial.get(enemy).transform == before


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
