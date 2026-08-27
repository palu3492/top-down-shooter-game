"""Many pursuers share one obstacle-aware direction field."""

from shooter.flow_field import (
    ROUTE_FOUND,
    UNREACHABLE,
    FlowField,
    NavigationRoutePlanner,
)
from shooter.world_collision import Aabb


def test_flow_field_routes_around_a_blocking_wall():
    field = FlowField(
        (500, 300),
        50,
        (20, 20),
        (Aabb(200, 0, 50, 200),),
    )
    field.rebuild((425, 250))

    direction = field.direction_at((125, 75))

    assert direction is not None
    assert direction[1] > 0


def test_flow_field_rebuilds_when_the_destination_changes_cell():
    field = FlowField((300, 300), 50, (20, 20), ())
    field.rebuild((275, 25))
    first = field.direction_at((25, 25))
    field.rebuild((25, 275))

    assert first == (1, 0)
    assert field.direction_at((25, 25)) == (0, 1)


def test_flow_field_offers_a_deterministic_recovery_direction():
    field = FlowField((300, 300), 50, (20, 20), ())
    field.rebuild((275, 275))
    preferred = field.direction_at((125, 125))

    recovery = field.recovery_direction_at((125, 125), 7, preferred)

    assert preferred == (1, 1)
    assert recovery != preferred
    assert recovery in (
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
    )


def test_navigation_route_chooses_a_way_around_a_wall():
    field = FlowField((500, 300), 50, (20, 20), (Aabb(200, 0, 50, 200),))

    route = field.route((125, 75), (425, 75))

    assert route.status == ROUTE_FOUND
    assert len(route.waypoints) >= 3
    assert any(waypoint[1] > 200 for waypoint in route.waypoints)


def test_navigation_route_reports_unreachable_when_the_goal_is_sealed():
    field = FlowField(
        (300, 300),
        50,
        (20, 20),
        (Aabb(100, 0, 50, 300),),
    )

    assert field.route((25, 25), (275, 25)).status == UNREACHABLE


def test_route_planner_reuses_routes_within_the_same_navigation_cells():
    planner = NavigationRoutePlanner(FlowField((300, 300), 50, (20, 20), ()))

    first = planner.route_for((25, 25), (275, 275))
    second = planner.route_for((40, 40), (260, 260))

    assert second is first
    assert (planner.requests, planner.cache_hits) == (2, 1)


def test_route_variants_can_choose_different_equal_cost_sides_of_a_wall():
    field = FlowField((500, 300), 50, (20, 20), (Aabb(200, 100, 50, 100),))

    upper = field.route((125, 175), (425, 175), variant=0)
    lower = field.route((125, 175), (425, 175), variant=4)

    assert upper.status == lower.status == ROUTE_FOUND
    assert upper.waypoints != lower.waypoints


def test_navigation_route_uses_diagonal_cells_in_open_space():
    route = FlowField((300, 300), 50, (20, 20), ()).route((25, 25), (275, 275))

    assert route.status == ROUTE_FOUND
    assert route.cells[:2] == ((0, 0), (1, 1))
    assert route.waypoints == ((25.0, 25.0), (275.0, 275.0))


def test_navigation_route_does_not_cut_diagonally_past_blocked_corners():
    field = FlowField(
        (150, 150),
        50,
        (20, 20),
        (Aabb(50, 0, 50, 50), Aabb(0, 50, 50, 50)),
    )

    assert field.route((25, 25), (125, 125)).status == UNREACHABLE
