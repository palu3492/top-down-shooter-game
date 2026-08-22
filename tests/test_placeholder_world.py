"""Placeholder presentation binds immutable tags and values to debug shapes."""

from pathlib import Path

import pygame

from shooter.simulation_snapshot import (
    EntitySnapshot,
    MatchSnapshot,
    VitalSnapshot,
)
from shooter.ui.placeholder_world import (
    BALLISTIC,
    ENEMY,
    PLAYER,
    PlaceholderWorldRenderer,
    binding_for,
)
from shooter.session import Session
from shooter.viewport import Viewport


def entity(entity_id, tags, position=(50, 50), vitality=None):
    return EntitySnapshot(
        entity_id,
        frozenset(tags),
        None,
        position,
        None,
        vitality,
    )


def snapshot(*entities):
    return MatchSnapshot("test", "arena", 1, "running", 10, entities)


def test_stable_tags_choose_debug_bindings_without_actor_types():
    assert binding_for(entity(1, ("actor", "player"))) is PLAYER
    assert binding_for(entity(2, ("actor", "enemy"))) is ENEMY
    assert binding_for(entity(3, ("attack", "ballistic"))) is BALLISTIC


def test_renderer_draws_snapshot_positions_with_camera_offset():
    surface = pygame.Surface((120, 100))
    surface.fill((0, 0, 0))
    actor = entity(
        1,
        ("actor", "player"),
        (40, 50),
        VitalSnapshot(75, 100, 0, 0, True),
    )

    PlaceholderWorldRenderer().draw(surface, snapshot(actor), camera=(10, -5))

    assert surface.get_at((50, 45))[:3] == PLAYER.colour
    assert surface.get_at((50, 13))[:3] != (0, 0, 0)


def test_renderer_does_not_import_or_inspect_legacy_actor_modules():
    source = Path("shooter/ui/placeholder_world.py").read_text()

    assert "shooter.entities" not in source
    assert ".entity" not in source
    assert "pygame.sprite" not in source


def test_legacy_attacks_and_pickups_enter_snapshot_through_stable_tags(display):
    session = Session(Viewport((1080, 720)))

    session._shoot()
    tags = {tag for item in session.snapshot.entities for tag in item.tags}

    assert "melee" in tags
    assert "powerup" in tags
