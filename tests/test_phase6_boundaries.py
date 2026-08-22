"""Executable reusable-spawning exit audit."""

import ast
import random
from pathlib import Path

from shooter.actor_creation import (
    ActorCreationResult,
    ActorDefinition,
)
from shooter.map_definition import SpawnPoint
from shooter.spatial import Box, SpatialStore, Transform
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import SpawnActorRequest, SpawnService
from shooter.world_registry import WorldRegistry


class NeutralRecordingFactory:
    def create(self, window, definition, request):
        return ActorCreationResult(
            definition.definition_id,
            definition.actor_kind,
            definition.faction,
            request.position,
            definition.max_health,
            definition.collision_size,
            definition.movement_speed,
        )


def test_non_survival_faction_uses_the_same_spawn_service_and_world_stores():
    definition = ActorDefinition(
        "team_soldier", "soldier", "team_a", 125, (40, 40), 160
    )
    source = SpawnPoint(
        "alpha", (250, 300), role="team_a", faction="team_a", actor_kind="soldier"
    )
    result = SpawnService(NeutralRecordingFactory(), random.Random(7)).spawn(
        SpawnActorRequest(
            definition,
            SpawnQuery(role="team_a", faction="team_a", actor_kind="soldier"),
            PlacementConstraints(),
            count=1,
        ),
        (source,),
        (1080, 720),
    )
    registry = WorldRegistry()
    spatial = SpatialStore()
    actor = result.actors[0]
    actor_id = registry.register(actor, ("actor", actor.faction))
    spatial.attach(actor_id, Transform(*actor.position), Box(*actor.collision_size))

    assert result.complete is True
    assert actor.actor_kind == "soldier"
    assert registry.get(actor_id) is actor
    assert spatial.get(actor_id).transform == Transform(250, 300)


def test_survival_rules_do_not_construct_actors_or_choose_coordinates():
    forbidden_calls = {"Zombie", "randint", "uniform", "set_position"}
    found = []
    for filename in ("shooter/systems/waves.py", "shooter/systems/levels.py"):
        tree = ast.parse(Path(filename).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", getattr(node.func, "attr", None))
                if name in forbidden_calls:
                    found.append((filename, name))

    assert found == []


def test_neutral_spawn_pipeline_has_no_pygame_dependency():
    modules = (
        "shooter/actor_creation.py",
        "shooter/spawn_selection.py",
        "shooter/spawn_fallback.py",
        "shooter/spawn_service.py",
    )
    pygame_imports = []
    for filename in modules:
        tree = ast.parse(Path(filename).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            if "pygame" in names:
                pygame_imports.append(filename)

    assert pygame_imports == []
