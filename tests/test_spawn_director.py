"""Shared spawn pacing is deterministic and independent of mode policy."""

import ast
from pathlib import Path

import pytest

from shooter.spawn_director import (
    SpawnBudget,
    SpawnDirector,
    SpawnDirectorPolicy,
)


def test_director_releases_an_immediate_burst_then_observes_its_interval():
    director = SpawnDirector(
        SpawnDirectorPolicy(
            burst_size=2,
            interval_seconds=1.0,
            activation_delay_seconds=0.75,
        )
    )
    director.queue((SpawnBudget("walker", 5),))

    first = director.advance(0.0)
    waiting = director.advance(0.5)
    second = director.advance(0.5)

    assert [(item.definition, item.count) for item in first] == [("walker", 2)]
    assert waiting == ()
    assert [(item.count, item.sequence) for item in second] == [(2, 1)]
    assert first[0].activation_delay_seconds == 0.75
    assert director.remaining == 1


def test_director_preserves_budget_order_and_catches_up_deterministically():
    director = SpawnDirector(SpawnDirectorPolicy(burst_size=2, interval_seconds=1))
    director.queue((SpawnBudget("walker", 3), SpawnBudget("runner", 2)))

    first = director.advance(0)
    later = director.advance(2)

    assert [(item.definition, item.count) for item in (*first, *later)] == [
        ("walker", 2),
        ("walker", 1),
        ("runner", 2),
    ]
    assert director.active is False


def test_director_rejects_invalid_policy_budget_and_time():
    with pytest.raises(ValueError):
        SpawnDirectorPolicy(burst_size=0)
    with pytest.raises(ValueError):
        SpawnBudget("walker", -1)
    with pytest.raises(ValueError):
        SpawnDirector().advance(-0.1)


def test_spawn_director_has_no_pygame_mode_or_actor_factory_dependency():
    imports = set()
    source = Path("shooter/spawn_director.py").read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(
        name == "pygame"
        or name.startswith("shooter.modes")
        or name == "shooter.actor_creation"
        for name in imports
    )
