"""Neutral actor definitions and explicit creation requests."""

import ast
from pathlib import Path

import pytest

from shooter.actor_creation import (
    ActorCreationRequest,
    ActorCreationService,
    ActorDefinition,
)


def walker():
    return ActorDefinition("walker", "walker", "horde", 100, (64, 64), 120)


def test_same_definition_creates_state_at_two_explicit_positions():
    service = ActorCreationService()
    definition = walker()

    first = service.create(definition, ActorCreationRequest("walker", (10, 20)))
    second = service.create(definition, ActorCreationRequest("walker", (300, 400)))

    assert first.position == (10, 20)
    assert second.position == (300, 400)
    assert first.definition_id == second.definition_id == "walker"
    assert first.faction == second.faction == "horde"


def test_mismatched_definition_request_is_rejected():
    with pytest.raises(ValueError, match="does not match"):
        ActorCreationService().create(
            walker(), ActorCreationRequest("survivor", (10, 20))
        )


def test_actor_creation_values_have_no_pygame_dependency():
    source = Path("shooter/actor_creation.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports
