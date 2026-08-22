"""Headless authoritative transforms and collision-shape definitions."""

from dataclasses import FrozenInstanceError

import pytest

from shooter import commands, config
from shooter.session import PLAYER_SOLID, Session
from shooter.spatial import Bounds, Box, Circle, SpatialStore, Transform
from shooter.viewport import Viewport
from shooter.world_registry import EntityId

WINDOW = (1080, 720)


def test_spatial_state_is_created_queried_updated_and_removed_headlessly():
    spatial = SpatialStore()
    entity_id = EntityId(7)
    box = Box(40, 24, offset_y=3)

    attached = spatial.attach(entity_id, Transform(10, 20), box)
    moved = spatial.move_to(entity_id, 35, 45)
    circled = spatial.set_collision(entity_id, Circle(12))

    assert attached.transform == Transform(10, 20)
    assert moved.transform == Transform(35, 45)
    assert circled.collision == Circle(12)
    assert spatial.get(entity_id) is circled
    assert spatial.remove(entity_id) is circled
    assert entity_id not in spatial


def test_spatial_values_are_immutable_and_ids_cannot_be_attached_twice():
    spatial = SpatialStore()
    entity_id = EntityId(1)
    transform = Transform(1, 2)
    spatial.attach(entity_id, transform)

    with pytest.raises(FrozenInstanceError):
        transform.x = 9
    with pytest.raises(ValueError, match="already has spatial state"):
        spatial.attach(entity_id, Transform(3, 4))


def test_world_bounds_clamp_transforms_without_pygame_geometry():
    bounds = Bounds(10, 20, 100, 200)

    assert bounds.clamp(Transform(-5, 250)) == Transform(10, 200)
    assert bounds.clamp(Transform(50, 60)) == Transform(50, 60)


def test_player_bridge_records_world_position_independent_of_viewport(display):
    window = Viewport(WINDOW)
    session = Session(window)
    state = session.spatial.get(session.player_id)
    original = state.transform
    camera_before = session.camera

    assert (original.x, original.y) == session._muzzle()
    assert state.collision == Box(*PLAYER_SOLID)

    window.resize((800, 600))
    session.resize()

    assert session.spatial.get(session.player_id).transform == original
    assert session.camera != camera_before
    assert session._muzzle() == (original.x, original.y)


def test_player_commands_move_world_transform_before_camera(display):
    session = Session(Viewport(WINDOW))
    before = session.spatial.get(session.player_id).transform

    session.step_controls(commands.ControlFrame(move=(1, -1)))

    after = session.spatial.get(session.player_id).transform
    distance = config.PLAYER_SPEED * config.SIM_DT
    assert after == Transform(before.x + distance, before.y - distance)
    assert session.camera == (
        session.window[0] / 2 - after.x,
        session.window[1] / 2 - after.y,
    )
