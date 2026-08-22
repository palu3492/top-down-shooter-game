"""Presentation receives immutable copies, never authoritative state objects."""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from shooter.application import MatchHost
from shooter.loadout import Loadout
from shooter.spatial import Box, Transform
from shooter import weapons
from shooter.simulation_snapshot import MutableSnapshotValueError


def test_snapshot_copies_authoritative_entity_combat_and_weapon_state():
    match = MatchHost().start()
    entity_id = match.entities.register(object(), ("actor", "player"))
    match.spatial.attach(entity_id, Transform(40, 60), Box(20, 30))
    match.combat.attach(entity_id, 100, health=75, armor=10, max_armor=20)
    match.factions.assign(entity_id, "survivors")
    loadout = Loadout((weapons.equip(weapons.M16),))

    snapshot = match.snapshot(loadouts={entity_id: loadout})
    actor = snapshot.entity(entity_id)

    assert actor.tags == {"actor", "player"}
    assert actor.faction == "survivors"
    assert actor.position == (40, 60)
    assert actor.collision.kind == "box"
    assert actor.vitality.health == 75
    assert actor.vitality.armor == 10
    assert actor.weapons[0].weapon_id == weapons.M16.id
    assert actor.weapons[0].selected is True


def test_snapshot_cannot_mutate_or_follow_later_simulation_changes():
    match = MatchHost().start()
    entity_id = match.entities.register(object())
    match.spatial.attach(entity_id, Transform(10, 20))
    match.combat.attach(entity_id, 100)
    held = weapons.equip(weapons.M16)
    original_loaded = held.loaded
    loadout = Loadout((held,))
    snapshot = match.snapshot(loadouts={entity_id: loadout})

    match.spatial.move_to(entity_id, 90, 80)
    match.combat.deplete(entity_id, 25)
    held.loaded -= 1

    actor = snapshot.entity(entity_id)
    assert actor.position == (10, 20)
    assert actor.vitality.health == 100
    assert actor.weapons[0].loaded == original_loaded
    with pytest.raises(FrozenInstanceError):
        actor.position = (0, 0)


def test_snapshot_contains_only_ids_and_values_not_registered_actor_objects():
    match = MatchHost().start()
    actor_object = object()
    entity_id = match.entities.register(actor_object)

    snapshot = match.snapshot()

    assert snapshot.entity(entity_id).entity_id == entity_id
    assert not hasattr(snapshot.entity(entity_id), "entity")


def test_snapshot_module_has_no_direct_pygame_or_presentation_dependency():
    source = Path("shooter/simulation_snapshot.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "pygame" not in {name.split(".")[0] for name in imports}
    assert not any(name.startswith("shooter.ui") for name in imports)


def test_mutable_mode_values_cannot_hide_inside_a_frozen_snapshot():
    match = MatchHost().start()

    with pytest.raises(MutableSnapshotValueError, match="mode_status"):
        match.snapshot(mode_status={"wave": 1})
