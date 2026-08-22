"""Modes share neutral actor registration and movement orchestration."""

import ast
from pathlib import Path

from shooter.actor_creation import ActorDefinition
from shooter.map_definition import MapDefinition, SpawnPoint
from shooter.match import Match
from shooter.match_actors import move_match_actor, spawn_match_actors
from shooter.match_configuration import (
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import SpawnActorRequest


def match():
    definition = MapDefinition(
        "arena", "Arena", "unused.tmx", (400, 300), capabilities=frozenset(("bounds",))
    )
    mode = ModeDescriptor("test", "Test", "")
    resolved = MatchConfigurationResolver(
        ModeCatalog((mode,)), MapCatalog((definition,))
    ).resolve(MatchConfiguration("test", "arena", 3))
    return Match(resolved)


def test_shared_spawn_registers_every_authoritative_actor_capability():
    owner = match()
    definition = ActorDefinition("runner", "soldier", "green", 125, (20, 20), 80)
    registered = spawn_match_actors(
        owner,
        SpawnActorRequest(
            definition,
            SpawnQuery(role="player", faction="green", actor_kind="soldier"),
            PlacementConstraints(),
            1,
        ),
        (
            SpawnPoint(
                "start",
                (30, 40),
                role="player",
                faction="green",
                actor_kind="soldier",
            ),
        ),
        "actors",
        tags=("player",),
    )
    (actor_id,) = registered.actor_ids

    assert owner.entities.tags_for(actor_id) == {"actor", "green", "player"}
    assert owner.spatial.get(actor_id).transform.x == 30
    assert owner.combat.get(actor_id).health == 125
    assert owner.factions.faction_of(actor_id) == "green"

    move_match_actor(owner, actor_id, (1, 0), 0.5)
    assert owner.spatial.get(actor_id).transform.x == 70


def test_match_actor_utilities_are_pygame_and_mode_independent():
    imports = set()
    for node in ast.walk(ast.parse(Path("shooter/match_actors.py").read_text())):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(
        name == "pygame" or name.startswith("shooter.modes") for name in imports
    )
