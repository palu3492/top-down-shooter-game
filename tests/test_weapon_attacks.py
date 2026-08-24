"""Neutral attributed attack descriptions precede pygame adaptation."""

import ast
import math
import random
from pathlib import Path

from shooter.weapon_attacks import AttackDescriptionService, damage_at_distance
from shooter.weapon_state import WeaponDefinition
from shooter.world_registry import EntityId


def ballistic(**changes):
    values = {
        "definition_id": "shotgun",
        "attack_kind": "ballistic",
        "damage": 14,
        "rate": 1.2,
        "magazine_capacity": 8,
        "reserve_capacity": 40,
        "pellets": 4,
        "spread": 20,
    }
    values.update(changes)
    return WeaponDefinition(**values)


def test_ballistic_descriptions_are_primitive_and_attributed():
    owner = EntityId(7)
    attacks = AttackDescriptionService().create(
        ballistic(spread=0), owner, (10, 20), (100, 0), random.Random(1)
    )

    assert len(attacks) == 4
    assert all(attack.instigator_id == owner for attack in attacks)
    assert all(attack.weapon_id == "shotgun" for attack in attacks)
    assert all(attack.attack_kind == "ballistic" for attack in attacks)
    assert all(attack.origin == (10, 20) for attack in attacks)
    assert all(attack.direction == (100, 0) for attack in attacks)


def test_seeded_spread_is_deterministic_before_adaptation():
    service = AttackDescriptionService()

    first = service.create(
        ballistic(), EntityId(1), (0, 0), (100, 0), random.Random(91)
    )
    second = service.create(
        ballistic(), EntityId(1), (0, 0), (100, 0), random.Random(91)
    )

    assert first == second
    assert len({attack.direction for attack in first}) > 1


def test_spread_remains_inside_the_configured_cone_and_preserves_reach():
    attacks = AttackDescriptionService().create(
        ballistic(pellets=40, spread=20),
        EntityId(1),
        (0, 0),
        (100, 0),
        random.Random(18),
    )

    assert all(math.isclose(math.hypot(*attack.direction), 100) for attack in attacks)
    assert all(
        abs(math.degrees(math.atan2(attack.direction[1], attack.direction[0]))) <= 10
        for attack in attacks
    )


def test_data_defined_range_falloff_is_clamped_at_effective_and_maximum_ranges():
    weapon = ballistic(
        damage=100,
        max_range=1000,
        effective_range=400,
        minimum_damage_fraction=0.4,
    )

    assert damage_at_distance(weapon, 0) == 100
    assert damage_at_distance(weapon, 400) == 100
    assert damage_at_distance(weapon, 700) == 70
    assert damage_at_distance(weapon, 1000) == 40
    assert damage_at_distance(weapon, 2000) == 40


def test_weapons_without_a_valid_falloff_profile_keep_base_damage():
    assert damage_at_distance(ballistic(damage=14), 999) == 14
    assert damage_at_distance(
        ballistic(damage=14, max_range=400, effective_range=400), 999
    ) == 14


def test_melee_description_carries_sweep_geometry():
    knife = WeaponDefinition(
        definition_id="knife",
        attack_kind="melee",
        damage=40,
        rate=2,
        reach=90,
        arc=45,
    )

    (attack,) = AttackDescriptionService().create(
        knife, EntityId(3), (4, 5), (0, 20), random.Random(1)
    )

    assert (attack.reach, attack.arc) == (90, 45)
    assert attack.damage == 40


def test_attack_description_module_has_no_pygame_dependency():
    source = Path("shooter/weapon_attacks.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports
