"""Executable Phase 5 ownership and adapter audit."""

import ast
import random
from pathlib import Path

from shooter.weapon_attacks import AttackDescriptionService
from shooter.weapon_state import (
    BEGIN_ATTACK,
    FIRE,
    WeaponDefinition,
    WeaponOperationRequest,
    WeaponOperationService,
    WeaponRuntime,
)
from shooter.world_registry import EntityId


def test_non_player_owner_uses_the_same_neutral_weapon_pipeline():
    bot_id = EntityId(41)
    definition = WeaponDefinition(
        definition_id="bot_rifle",
        attack_kind="ballistic",
        damage=18,
        rate=5,
        magazine_capacity=20,
        reserve_capacity=40,
    )
    runtime = WeaponRuntime.fresh(definition)
    operations = WeaponOperationService()

    begun = operations.apply(
        definition, runtime, WeaponOperationRequest(BEGIN_ATTACK)
    )
    attacks = AttackDescriptionService().create(
        definition, bot_id, (10, 15), (30, 0), random.Random(8)
    )
    fired = operations.apply(definition, runtime, WeaponOperationRequest(FIRE))

    assert begun.accepted is True
    assert fired.accepted is True
    assert runtime.loaded == 19
    assert len(attacks) == 1
    assert attacks[0].instigator_id == bot_id
    assert attacks[0].weapon_id == "bot_rifle"


def test_only_projectile_adapter_constructs_attack_sprites():
    constructors = []
    for path in Path("shooter").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id in {"Shot", "Swing"}:
                constructors.append(path.as_posix())

    assert set(constructors) == {"shooter/projectile_adapter.py"}


def test_session_and_shop_do_not_mutate_weapon_operation_fields_directly():
    forbidden = {"loaded", "reserve", "locked_for", "cooling_for"}
    mutations = []
    for filename in ("shooter/session.py", "shooter/systems/shop.py"):
        tree = ast.parse(Path(filename).read_text())
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
            elif isinstance(node, ast.AugAssign):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr in forbidden:
                    mutations.append((filename, target.attr))

    assert mutations == []
