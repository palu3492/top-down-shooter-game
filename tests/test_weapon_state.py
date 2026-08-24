"""Neutral weapon configuration and per-instance operation state."""

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from shooter.weapon_state import (
    AUTOMATIC,
    BURST,
    ADVANCE,
    BEGIN_ATTACK,
    FIRE,
    MANUAL_RELOAD,
    NO_AMMO,
    REFILL,
    RELOAD,
    WeaponDefinition,
    EquippedWeapon,
    WeaponOperationRequest,
    WeaponOperationService,
    WeaponRuntime,
)


def rifle_definition():
    return WeaponDefinition(
        definition_id="rifle",
        attack_kind="ballistic",
        damage=20,
        rate=6,
        magazine_capacity=30,
        reserve_capacity=90,
        reload_seconds=1.5,
        ammo_id="rifle_round",
    )


def test_weapon_definitions_are_immutable_configuration():
    definition = rifle_definition()

    with pytest.raises(FrozenInstanceError):
        definition.damage = 99


def test_two_runtime_instances_do_not_share_ammo_or_timers():
    definition = rifle_definition()
    first = WeaponRuntime.fresh(definition)
    second = WeaponRuntime.fresh(definition)

    first.loaded -= 1
    first.cooldown_remaining = 0.25
    first.reload_remaining = 1.0

    assert (second.loaded, second.reserve) == (30, 90)
    assert second.cooldown_remaining == 0
    assert second.reload_remaining == 0


def test_melee_runtime_has_no_ammunition():
    definition = WeaponDefinition(
        definition_id="knife",
        attack_kind="melee",
        damage=40,
        rate=2,
        reach=90,
        arc=45,
    )

    runtime = WeaponRuntime.fresh(definition)

    assert runtime.loaded is None
    assert runtime.reserve is None


def test_explicit_firing_modes_control_held_trigger_behavior():
    automatic = EquippedWeapon(replace(rifle_definition(), firing_mode=AUTOMATIC))
    burst = EquippedWeapon(
        replace(rifle_definition(), firing_mode=BURST, burst_size=2)
    )

    automatic.trigger_pressed()
    automatic.advance(1)
    assert automatic.trigger_held().accepted is True
    burst.trigger_pressed()
    burst.record_shot()
    burst.advance(1)
    assert burst.trigger_held().accepted is True


@pytest.mark.parametrize("step", (1 / 30, 1 / 60, 1 / 120))
def test_automatic_fire_cadence_is_consistent_across_simulation_step_rates(step):
    weapon = EquippedWeapon(replace(rifle_definition(), firing_mode=AUTOMATIC))
    starting_rounds = weapon.runtime.loaded

    assert weapon.trigger_pressed().accepted is True
    for _ in range(round(1 / step)):
        weapon.advance(step)
        weapon.trigger_held()

    assert starting_rounds - weapon.runtime.loaded == 7


def test_weapon_definition_rejects_unknown_or_one_shot_burst_modes():
    with pytest.raises(ValueError, match="unknown firing mode"):
        replace(rifle_definition(), firing_mode="laser")
    with pytest.raises(ValueError, match="at least two"):
        replace(rifle_definition(), firing_mode=BURST, burst_size=1)


def test_neutral_weapon_state_has_no_pygame_dependency():
    source = Path("shooter/weapon_state.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports


def test_fire_consumes_ammo_and_automatically_reloads_the_last_round():
    definition = rifle_definition()
    runtime = WeaponRuntime.fresh(definition)
    runtime.loaded = 1
    service = WeaponOperationService()

    result = service.apply(definition, runtime, WeaponOperationRequest(FIRE))

    assert result.accepted is True
    assert (result.rounds_spent, result.rounds_loaded) == (1, 30)
    assert result.status == RELOAD
    assert (runtime.loaded, runtime.reserve) == (30, 60)


def test_empty_weapon_rejects_fire_without_mutation():
    definition = rifle_definition()
    runtime = WeaponRuntime.fresh(definition)
    runtime.loaded = runtime.reserve = 0
    service = WeaponOperationService()

    result = service.apply(definition, runtime, WeaponOperationRequest(FIRE))

    assert result.accepted is False
    assert result.status == NO_AMMO
    assert result.rounds_spent == 0


def test_manual_reload_and_timer_advance_are_neutral_operations():
    definition = rifle_definition()
    runtime = WeaponRuntime.fresh(definition)
    runtime.loaded = 10
    service = WeaponOperationService()

    reloaded = service.apply(
        definition, runtime, WeaponOperationRequest(MANUAL_RELOAD)
    )
    advanced = service.apply(
        definition, runtime, WeaponOperationRequest(ADVANCE, 1.5)
    )

    assert reloaded.rounds_loaded == 20
    assert advanced.status is None
    assert runtime.reload_remaining == 0


def test_independent_owners_use_the_same_operation_service():
    definition = rifle_definition()
    first = WeaponRuntime.fresh(definition)
    second = WeaponRuntime.fresh(definition)
    service = WeaponOperationService()

    service.apply(definition, first, WeaponOperationRequest(BEGIN_ATTACK))
    service.apply(definition, first, WeaponOperationRequest(FIRE))

    assert first.loaded == 29
    assert service.ready(definition, first) is False
    assert second.loaded == 30
    assert service.ready(definition, second) is True


def test_refill_is_an_explicit_operation():
    definition = rifle_definition()
    runtime = WeaponRuntime.fresh(definition)
    runtime.reserve = 12

    result = WeaponOperationService().apply(
        definition, runtime, WeaponOperationRequest(REFILL)
    )

    assert result.accepted is True
    assert result.rounds_loaded == 78
    assert runtime.reserve == 90
