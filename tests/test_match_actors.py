"""Modes share neutral actor registration and movement orchestration."""

import ast
from pathlib import Path

from shooter.actor_creation import ActorDefinition
from shooter.domain_events import EntityRemoved
from shooter.map_definition import MapDefinition, SpawnPoint
from shooter.match import Match
from shooter.match_actors import (
    move_match_actor,
    remove_match_actor,
    spawn_match_actors,
)
from shooter.match_configuration import (
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.spawn_selection import PlacementConstraints, SpawnQuery
from shooter.spawn_service import SpawnActorRequest
from shooter.world_collision import Aabb, Polygon


def match(collision=(), playable_areas=()):
    definition = MapDefinition(
        "arena",
        "Arena",
        "unused.tmx",
        (400, 300),
        collision=collision,
        playable_areas=playable_areas,
        capabilities=frozenset(("bounds",)),
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


def test_shared_removal_clears_every_actor_capability_and_emits_reason():
    owner = match()
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    registered = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("start", (30, 20)),),
        "removal-runner",
    )
    actor_id = registered.actor_ids[0]
    owner.events.drain()

    removed = remove_match_actor(owner, actor_id, reason="defeated")

    assert removed.definition_id == "runner"
    assert actor_id not in owner.entities
    assert actor_id not in owner.spatial
    assert actor_id not in owner.combat
    assert owner.factions.faction_of(actor_id) is None
    assert owner.events.drain() == (EntityRemoved(actor_id, "defeated"),)
    assert remove_match_actor(owner, actor_id) is None


def test_shared_movement_stops_flush_against_authored_collision():
    owner = match((Aabb(75, 0, 20, 300),))
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    registered = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("start", (30, 40)),),
        "collision-runner",
    )
    actor_id = registered.actor_ids[0]

    move_match_actor(owner, actor_id, (1, 0), 1.0)

    stopped = owner.spatial.get(actor_id).transform
    assert 64.99 < stopped.x <= 65
    assert stopped.y == 40


def test_shared_movement_keeps_actor_inside_authored_playable_area():
    owner = match(playable_areas=(Polygon(((20, 20), (200, 20), (200, 180), (20, 180))),))
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    actor_id = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("start", (50, 50)),),
        "playable-area-runner",
    ).actor_ids[0]

    move_match_actor(owner, actor_id, (-1, 0), 1.0)

    assert 29.99 < owner.spatial.get(actor_id).transform.x <= 30


def test_movement_filters_distant_collision_shapes_without_missing_nearby_ones():
    collision = (
        Aabb(75, 0, 20, 300),
        *(Aabb(10_000 + index, 0, 1, 1) for index in range(100)),
    )
    owner = match(collision)
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    actor_id = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("start", (30, 40)),),
        "broad-phase-runner",
    ).actor_ids[0]

    move_match_actor(owner, actor_id, (1, 0), 1.0)

    assert owner.spatial.get(actor_id).transform.x <= 65


def test_shared_movement_slides_along_collision_on_the_unblocked_axis():
    owner = match((Aabb(75, 0, 20, 300),))
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    registered = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("start", (65, 40)),),
        "sliding-runner",
    )
    actor_id = registered.actor_ids[0]

    move_match_actor(owner, actor_id, (1, 1), 0.5)

    moved = owner.spatial.get(actor_id).transform
    assert moved.x == 65
    assert moved.y > 40


def test_cardinal_input_slides_along_an_angled_authored_collider():
    owner = match((Polygon(((80, 0), (100, 0), (20, 100), (0, 100))),))
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    actor_id = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("start", (30, 20)),),
        "angled-sliding-runner",
    ).actor_ids[0]

    move_match_actor(owner, actor_id, (1, 0), 1.0)

    moved = owner.spatial.get(actor_id).transform
    assert moved.y != 20


def test_dynamic_actor_occupancy_is_explicit_and_configurable():
    owner = match()
    definition = ActorDefinition("runner", "soldier", "green", 100, (20, 20), 80)
    mover = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("mover", (50, 40)),),
        "occupancy-mover",
    ).actor_ids[0]
    blocker = spawn_match_actors(
        owner,
        SpawnActorRequest(definition, SpawnQuery(), PlacementConstraints(), 1),
        (SpawnPoint("blocker", (80, 40)),),
        "occupancy-blocker",
    ).actor_ids[0]

    move_match_actor(owner, mover, (1, 0), 1.0, occupied_ids=(blocker,))

    stopped = owner.spatial.get(mover).transform
    assert 59.99 < stopped.x <= 60

    move_match_actor(owner, mover, (-1, 0), 0.25)
    assert owner.spatial.get(mover).transform.x < stopped.x
