"""The navigation inspection overlay is presentation-only."""

from types import SimpleNamespace

import pygame

from shooter.flow_field import FlowField
from shooter.simulation_snapshot import MatchSnapshot
from shooter.ui.navigation_debug import NavigationDebugRenderer
from shooter.world_collision import Aabb


def test_navigation_debug_draws_visible_grid_goal_and_summary(display):
    navigation = FlowField((400, 300), 100, (20, 20), (Aabb(100, 0, 100, 100),))
    navigation.rebuild((350, 250))
    snapshot = MatchSnapshot(
        "zombie_survival",
        "arena",
        1,
        "running",
        1,
        (),
        SimpleNamespace(stuck_enemy_ids=()),
    )
    surface = pygame.Surface((400, 300))
    surface.fill((0, 0, 0))

    NavigationDebugRenderer().draw(surface, snapshot, (0, 0), navigation)

    assert surface.get_at((50, 50))[:3] != (0, 0, 0)
    assert surface.get_at((250, 250))[:3] != (0, 0, 0)


def test_navigation_debug_caches_a_route_for_the_nearest_enemy(display):
    navigation = FlowField((500, 300), 50, (20, 20), (Aabb(200, 0, 50, 200),))
    navigation.rebuild((425, 75))
    snapshot = MatchSnapshot(
        "zombie_survival",
        "arena",
        1,
        "running",
        1,
        (
            SimpleNamespace(
                entity_id=1, tags=frozenset(("player",)), position=(425, 75)
            ),
            SimpleNamespace(
                entity_id=2, tags=frozenset(("enemy",)), position=(125, 75)
            ),
        ),
        SimpleNamespace(stuck_enemy_ids=()),
    )
    renderer = NavigationDebugRenderer()

    route = renderer._route_for(snapshot, navigation)

    assert route.status == "found"
    assert len(route.waypoints) >= 3
