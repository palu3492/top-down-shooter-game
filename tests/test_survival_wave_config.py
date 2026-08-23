"""Survival wave composition is immutable data over neutral actor definitions."""

from dataclasses import FrozenInstanceError

import pytest

from shooter.actor_creation import ActorDefinition
from shooter.modes.zombie_survival import EnemyWaveRule, SurvivalWavePlan


WALKER = ActorDefinition("walker", "walker", "horde", 100, (56, 56), 360)
SPRINTER = ActorDefinition("sprinter", "sprinter", "horde", 60, (40, 40), 520)


def test_wave_plan_describes_multiple_enemy_types_and_growth():
    plan = SurvivalWavePlan(
        (
            EnemyWaveRule(WALKER, 5, growth=1, exponent=2),
            EnemyWaveRule(SPRINTER, 0, growth=2),
        ),
        preparation_seconds=10,
    )

    assert plan.composition(1) == (("walker", 5),)
    assert plan.composition(3) == (("walker", 9), ("sprinter", 4))


def test_wave_rules_can_introduce_an_enemy_at_a_specific_wave():
    plan = SurvivalWavePlan(
        (EnemyWaveRule(WALKER, 5, growth=2), EnemyWaveRule(SPRINTER, 2, starts_at=3)),
        preparation_seconds=25,
    )

    assert plan.composition(1) == (("walker", 5),)
    assert plan.composition(3) == (("walker", 9), ("sprinter", 2))
    assert plan.composition(5) == (("walker", 13), ("sprinter", 2))


def test_wave_configuration_rejects_invalid_or_ambiguous_values():
    with pytest.raises(ValueError):
        EnemyWaveRule(WALKER, -1)
    with pytest.raises(ValueError):
        SurvivalWavePlan((EnemyWaveRule(WALKER, 1),), -1)
    with pytest.raises(ValueError):
        SurvivalWavePlan(
            (EnemyWaveRule(WALKER, 1), EnemyWaveRule(WALKER, 2)), 1
        )


def test_wave_configuration_is_immutable():
    rule = EnemyWaveRule(WALKER, 1)

    with pytest.raises(FrozenInstanceError):
        rule.base_count = 4
