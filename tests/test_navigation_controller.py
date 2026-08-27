"""Waypoint following is deterministic and has no game-mode dependency."""

import ast
from pathlib import Path

import pytest

from shooter.flow_field import NavigationRoute, ROUTE_FOUND
from shooter.navigation_controller import RouteProgress, WaypointFollower


def route():
    return NavigationRoute(
        ROUTE_FOUND,
        ((0, 0), (1, 0), (1, 1)),
        ((50.0, 50.0), (150.0, 50.0), (150.0, 150.0)),
    )


def test_follower_advances_waypoints_only_after_reaching_them():
    follower = WaypointFollower(arrival_distance=20)
    progress, direction = follower.advance(RouteProgress(route()), (50, 50))

    assert progress.waypoint_index == 1
    assert direction == (1.0, 0.0)

    progress, direction = follower.advance(progress, (150, 50))
    assert progress.waypoint_index == 2
    assert direction == (0.0, 1.0)


def test_follower_reports_completion_at_the_final_waypoint():
    progress, direction = WaypointFollower().advance(
        RouteProgress(route(), 2), (150, 150)
    )

    assert progress.complete is True
    assert direction == (0.0, 0.0)


def test_follower_preserves_a_diagonal_waypoint_direction():
    diagonal = NavigationRoute(
        ROUTE_FOUND,
        ((0, 0), (1, 1)),
        ((50.0, 50.0), (150.0, 150.0)),
    )

    _progress, direction = WaypointFollower().advance(
        RouteProgress(diagonal, 1), (50, 50)
    )

    assert direction == pytest.approx((2**-0.5, 2**-0.5))


def test_follower_rejects_non_positive_arrival_distance():
    with pytest.raises(ValueError, match="arrival_distance"):
        WaypointFollower(0)


def test_navigation_controller_has_no_pygame_or_mode_dependency():
    source = Path("shooter/navigation_controller.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(
        name == "pygame" or name.startswith("shooter.modes") for name in imports
    )
