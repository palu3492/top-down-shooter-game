"""Headless world-coordinate collision independent of sprites and cameras."""

from shooter.spatial import Box, Transform
from shooter.world_collision import Aabb, Ellipse, Polygon, actor_box, overlaps


def test_actor_box_uses_stable_shape_not_visual_dimensions():
    shape = Box(70, 50, offset_x=5)

    assert actor_box(Transform(100, 80), shape) == Aabb(70, 55, 70, 50)


def test_box_overlap_is_headless_and_edge_contact_is_not_penetration():
    actor = Aabb(10, 10, 20, 20)

    assert overlaps(actor, Aabb(25, 25, 20, 20)) is True
    assert overlaps(actor, Aabb(30, 10, 20, 20)) is False


def test_ellipse_respects_empty_corners_of_its_bounds():
    ellipse = Ellipse(100, 100, 100, 100)

    assert overlaps(Aabb(140, 140, 20, 20), ellipse) is True
    assert overlaps(Aabb(100, 100, 5, 5), ellipse) is False


def test_polygon_checks_edges_instead_of_only_its_bounds():
    triangle = Polygon(((0, 0), (100, 0), (0, 100)))

    assert overlaps(Aabb(45, 45, 20, 20), triangle) is True
    assert overlaps(Aabb(90, 90, 5, 5), triangle) is False
