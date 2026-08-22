"""Presentation camera follows stable IDs without owning world position."""

from shooter.camera import FollowCamera
from shooter.spatial import SpatialStore, Transform
from shooter.world_registry import EntityId


def test_camera_follows_selected_entity_and_clamps_to_world():
    spatial = SpatialStore()
    first = EntityId(1)
    second = EntityId(2)
    spatial.attach(first, Transform(500, 400))
    spatial.attach(second, Transform(1900, 1400))
    camera = FollowCamera((800, 600), (2000, 1500), spatial, first)

    assert camera.offset == (-100, -100)
    assert camera.follow(second) == (-1200, -900)


def test_resizing_camera_changes_only_presentation():
    spatial = SpatialStore()
    target = EntityId(1)
    position = Transform(700, 500)
    spatial.attach(target, position)
    camera = FollowCamera((800, 600), (2000, 1500), spatial, target)

    before = camera.offset
    after = camera.resize((1000, 800))

    assert after != before
    assert spatial.get(target).transform == position


def test_actor_movement_does_not_require_a_camera():
    spatial = SpatialStore()
    target = EntityId(1)
    spatial.attach(target, Transform(20, 30))

    spatial.move_to(target, 45, 60)

    assert spatial.get(target).transform == Transform(45, 60)
