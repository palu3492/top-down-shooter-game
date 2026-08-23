"""Neutral interaction context is distinct from mode-specific execution."""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from shooter.interactions import InteractionService
from shooter.map_definition import MapInteraction


def test_service_discovers_prompt_and_routes_available_intent():
    service = InteractionService()
    interaction = MapInteraction(
        "box",
        "weapon_station",
        position=(10, 0),
        properties=(("prompt", "PRESS E: BUY"),),
    )

    context = service.discover(7, (0, 0), (interaction,), 20)
    result = service.route_intent(7, context)

    assert context.prompt == "PRESS E: BUY"
    assert result.available is True
    assert (result.interaction_id, result.kind) == ("box", "weapon_station")
    with pytest.raises(FrozenInstanceError):
        context.prompt = "changed"


def test_missing_or_wrong_actor_context_is_explicitly_out_of_range():
    service = InteractionService()
    context = service.discover(
        7, (0, 0), (MapInteraction("door", "door", position=(0, 0)),), 1
    )

    assert service.route_intent(8, context).reason == "out_of_range"
    assert service.route_intent(7, None).available is False


def test_interaction_service_has_no_pygame_or_mode_dependency():
    imports = set()
    for node in ast.walk(ast.parse(Path("shooter/interactions.py").read_text())):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any(
        name == "pygame" or name.startswith("shooter.modes") for name in imports
    )
