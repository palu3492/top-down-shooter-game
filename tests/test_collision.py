import pygame

from shooter.collision import EllipseObstacle, PolygonObstacle, load_obstacles


def test_world_obstacles_keep_their_tiled_geometry():
    obstacles = (
        *load_obstacles("../tests/fixtures/maps/riverside.tmx"),
        *load_obstacles("../tests/fixtures/maps/crossroads.tmx"),
    )

    assert any(isinstance(item, EllipseObstacle) for item in obstacles)
    assert any(isinstance(item, PolygonObstacle) for item in obstacles)


def test_ellipse_does_not_block_the_empty_corner_of_its_bounds():
    ellipse = EllipseObstacle(100, 100, 100, 100)

    assert ellipse.colliderect(pygame.Rect(140, 140, 20, 20))
    assert not ellipse.colliderect(pygame.Rect(100, 100, 5, 5))


def test_polygon_collision_checks_edges_and_not_only_its_bounds():
    triangle = PolygonObstacle(((0, 0), (100, 0), (0, 100)))

    assert triangle.colliderect(pygame.Rect(45, 45, 20, 20))
    assert not triangle.colliderect(pygame.Rect(90, 90, 5, 5))
