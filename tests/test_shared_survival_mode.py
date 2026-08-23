"""The first Survival slice runs on neutral Match actors and stores."""

import ast
import math
from pathlib import Path

from shooter import config
from shooter.actor_creation import ActorDefinition
from shooter.domain_events import DamageApplied, EntityKilled
from shooter.map_definition import (
    MapDefinition,
    MapConstructionAnchor,
    MapHarvestable,
    MapInteraction,
    SpawnPoint,
    SpawnRegion,
)
from shooter.match import Match
from shooter.match_configuration import (
    ZOMBIE_SURVIVAL,
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    default_mode_catalog,
)
from shooter.modes.zombie_survival import (
    EnemyWaveRule,
    FireSurvivorWeapon,
    InteractSurvivor,
    MoveSurvivor,
    ReloadSurvivorWeapon,
    SelectSurvivorWeapon,
    SurvivalMode,
    SurvivalWavePlan,
    UseSurvivorTool,
)
from shooter.modes.zombie_survival.mode import BREAKER, SMG
from shooter.weapon_state import EquippedWeapon
from shooter.world_collision import Aabb, actor_box, overlaps


def resolved(interactions=(), harvestables=(), construction_anchors=()):
    definition = MapDefinition(
        "arena",
        "Arena",
        "unused.tmx",
        (1000, 800),
        capabilities=frozenset(("bounds",)),
        interactions=interactions,
        harvestables=harvestables,
        construction_anchors=construction_anchors,
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
    assert snapshot.mode_status.enemy_composition == (("walker", 5),)


def test_survival_snapshots_nearby_interaction_and_routes_explicit_intent():
    station = MapInteraction(
        "test-station",
        "weapon_station",
        position=(500, 400),
        properties=(
            ("kind", "weapon_station"),
            ("prompt", "PRESS E: TEST STATION"),
        ),
    )
    match = Match(resolved((station,)))
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)

    assert match.mode_status.interaction_context.prompt == "PRESS E: TEST STATION"
    match.advance(0.0, (InteractSurvivor(),))
    assert match.mode_status.interaction_result.available is True
    assert match.mode_status.interaction_result.interaction_id == "test-station"

    match.advance(1.0, (MoveSurvivor((1, 0)), InteractSurvivor()))
    assert match.mode_status.interaction_context is None
    assert match.mode_status.interaction_result.reason == "out_of_range"


def test_weapon_station_fills_the_second_survival_firearm_slot():
    station = MapInteraction(
        "smg-station",
        "weapon_station",
        position=(500, 400),
        properties=(
            ("kind", "weapon_station"),
            ("price", "50"),
            ("weapon_id", "survivor_smg"),
        ),
    )
    match = Match(resolved((station,)))
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    mode.cash.increase_cash(50)

    match.advance(0.0, (InteractSurvivor(),))

    status = match.mode_status
    assert status.purchase_result.success is True
    assert status.purchase_result.action == "purchased"
    assert status.cash == 0
    weapons = match.snapshot().entity(mode.player_id).weapons
    assert [weapon.weapon_id for weapon in weapons] == [
        "survivor_rifle",
        "survivor_smg",
    ]
    assert weapons[1].selected is True
    assert (weapons[1].loaded, weapons[1].reserve) == (40, 200)


def test_selection_keeps_each_survival_firearm_runtime_state_while_stowed():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    loadout = mode.loadouts[mode.player_id]
    smg = EquippedWeapon(SMG)
    smg.runtime.loaded = 17
    smg.runtime.reserve = 88
    loadout.add(smg, select=True)

    match.advance(0.0, (SelectSurvivorWeapon(0),))
    assert loadout.selected.definition.definition_id == "survivor_rifle"
    match.advance(0.0, (SelectSurvivorWeapon(1),))

    assert loadout.selected is smg
    assert (smg.runtime.loaded, smg.runtime.reserve) == (17, 88)
    assert loadout.select(2) is False


def test_survival_pickaxe_is_a_separate_configured_tool_role_that_can_melee():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    enemy_id = mode.enemy_ids[0]
    player = match.spatial.get(mode.player_id).transform
    match.spatial.move_to(enemy_id, player.x + 70, player.y)
    before = match.combat.get(enemy_id).health

    match.advance(0.0, (UseSurvivorTool((1, 0)),))

    snapshot = match.snapshot().entity(mode.player_id)
    assert snapshot.tool.weapon_id == "survivor_pickaxe"
    assert len(snapshot.weapons) == 1
    assert match.combat.get(enemy_id).health == before - 75


def test_survival_can_explicitly_omit_the_tool_role_without_affecting_firearms():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=1, tool_definition=None)
    match.start(mode)

    snapshot = match.snapshot().entity(mode.player_id)
    assert snapshot.tool is None
    assert snapshot.weapons[0].weapon_id == "survivor_rifle"


def test_pickaxe_harvesting_adds_map_authored_resources_to_match_state():
    tree = MapHarvestable(
        "tree-1",
        "tree",
        position=(540, 400),
        properties=(
            ("durability", "150"),
            ("resource_id", "wood"),
            ("resource_yield", "12"),
        ),
    )
    match = Match(resolved(harvestables=(tree,)))
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)

    match.advance(0.0, (UseSurvivorTool((1, 0)),))

    result = match.mode_status.harvest_result
    assert (result.success, result.harvestable_id) == (True, "tree-1")
    assert result.remaining_durability == 75
    assert (result.resource_id, result.resource_amount) == ("wood", 6)
    assert match.mode_status.resources == (("wood", 6),)
    assert mode.cash.balance == 0


def test_construction_anchor_builds_with_resources_and_repairs_transactionally():
    anchor = MapConstructionAnchor(
        "gate",
        "barricade",
        position=(500, 400),
        properties=(
            ("build_cost", "wood:4"),
            ("max_health", "100"),
            ("repair_cost", "wood:1"),
        ),
    )
    match = Match(resolved(construction_anchors=(anchor,)))
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    mode.resources.add("wood", 5)

    match.advance(0.0, (InteractSurvivor(),))
    built = match.mode_status.construction_result
    mode.barricades["gate"].health = 25
    match.advance(0.0, (InteractSurvivor(),))
    repaired = match.mode_status.construction_result

    assert (built.reason, built.health) == ("built", 100)
    assert (repaired.reason, repaired.health) == ("repaired", 100)
    assert match.mode_status.resources == (("wood", 0),)


def test_built_barricade_stops_and_is_damaged_by_an_enemy_contact():
    anchor = MapConstructionAnchor(
        "gate",
        "barricade",
        area=Aabb(450, 350, 20, 100),
        properties=(("build_cost", "wood:1"), ("max_health", "100")),
    )
    match = Match(resolved(construction_anchors=(anchor,)))
    mode = SurvivalMode(sources(), enemy_count=1)
    match.start(mode)
    mode.resources.add("wood", 1)
    match.advance(0.0, (InteractSurvivor(),))
    enemy_id = mode.enemy_ids[0]
    match.spatial.move_to(enemy_id, 430, 400)

    match.advance(1.0, ())

    assert mode.barricades["gate"].health < 100
    assert match.spatial.get(enemy_id).transform.x < 450


def test_breaker_applies_heavy_damage_to_a_barricade():
    anchor = MapConstructionAnchor(
        "gate",
        "barricade",
        area=Aabb(450, 350, 20, 100),
        properties=(("build_cost", "wood:1"), ("max_health", "100")),
    )
    match = Match(resolved(construction_anchors=(anchor,)))
    spawn_sources = (
        *sources(),
        SpawnRegion(
            "runners",
            Aabb(100, 100, 220, 500),
            role="enemy",
            faction="horde",
            actor_kind="runner",
        ),
        SpawnRegion(
            "breakers",
            Aabb(100, 100, 220, 500),
            role="enemy",
            faction="horde",
            actor_kind="breaker",
        ),
    )
    mode = SurvivalMode(spawn_sources)
    match.start(mode)
    mode.resources.add("wood", 1)
    match.advance(0.0, (InteractSurvivor(),))
    mode.wave = 5
    batch = mode._spawn_wave(match)
    breaker_id = next(
        entity_id
        for entity_id in batch[-1].actor_ids
        if match.entities.get(entity_id).definition_id == BREAKER.definition_id
    )
    match.spatial.move_to(breaker_id, 430, 400)

    match.advance(1.0, ())

    assert mode.barricades["gate"].health <= 100 - config.ZOMBIE_DAMAGE * 4


def test_wave_plan_spawns_multiple_neutral_enemy_definitions():
    sprinter = ActorDefinition("sprinter", "sprinter", "horde", 60, (40, 40), 520)
    plan = SurvivalWavePlan(
        (EnemyWaveRule(sprinter, 2),), preparation_seconds=1
    )
    spawn_sources = (
        *sources(),
        SpawnRegion(
            "sprinters",
            Aabb(650, 100, 200, 500),
            role="enemy",
            faction="horde",
            actor_kind="sprinter",
        ),
    )
    match = Match(resolved())
    mode = SurvivalMode(spawn_sources, wave_plan=plan)

    match.start(mode)

    assert len(mode.enemy_ids) == 2
    assert all(
        match.entities.get(enemy_id).definition_id == "sprinter"
        for enemy_id in mode.enemy_ids
    )
    assert match.mode_status.enemy_composition == (("sprinter", 2),)


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
    defeated = mode.retired_enemy_ids[0]
    assert defeated not in match.entities
    assert defeated not in match.spatial
    assert defeated not in match.combat
    match.advance(0.75)

    assert match.mode_status.phase == "combat"
    assert match.mode_status.wave == 2
    assert match.mode_status.enemies_remaining == 2
    assert match.mode_status.cash == config.KILL_REWARD
    assert len(mode.enemy_ids) == 2
    assert min(mode.enemy_ids) > defeated
    assert len(match.snapshot().entities) == 3


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


def test_enemy_crowding_avoids_other_enemies_but_allows_player_contact():
    match = Match(resolved())
    mode = SurvivalMode(sources(), enemy_count=2)
    match.start(mode)
    player = match.spatial.get(mode.player_id).transform
    first, second = mode.enemy_ids
    match.spatial.move_to(first, player.x - 100, player.y)
    match.spatial.move_to(second, player.x - 135, player.y)

    match.advance(1.0)

    first_state = match.spatial.get(first)
    second_state = match.spatial.get(second)
    assert not overlaps(
        actor_box(first_state.transform, first_state.collision),
        actor_box(second_state.transform, second_state.collision),
    )
    assert match.combat.get(mode.player_id).health < config.PLAYER_HEALTH


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
