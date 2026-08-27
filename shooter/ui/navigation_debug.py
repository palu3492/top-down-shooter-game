"""Optional in-game visualization of the derived navigation surface."""

import pygame


class NavigationDebugRenderer:
    def __init__(self):
        self._route_key = None
        self._cached_route = None

    def draw(self, surface, snapshot, camera, navigation, route_planner=None):
        if navigation is None:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._cells(overlay, camera, navigation)
        self._goal(overlay, camera, navigation)
        route = self._route_for(snapshot, navigation, route_planner)
        self._draw_route(overlay, camera, route)
        self._stuck(overlay, snapshot, camera)
        surface.blit(overlay, (0, 0))
        self._summary(surface, snapshot.mode_status, navigation, route)

    def _route_for(self, snapshot, navigation, route_planner=None):
        player = next(
            (entity for entity in snapshot.entities if "player" in entity.tags), None
        )
        enemies = tuple(
            entity
            for entity in snapshot.entities
            if "enemy" in entity.tags and entity.position is not None
        )
        if player is None or player.position is None or not enemies:
            self._route_key = None
            self._cached_route = None
            return None
        enemy = min(
            enemies,
            key=lambda entity: _distance(entity.position, player.position),
        )
        key = (
            enemy.entity_id,
            navigation.cell_at(enemy.position),
            navigation.cell_at(player.position),
        )
        if key != self._route_key:
            self._route_key = key
            planner = route_planner
            self._cached_route = (
                navigation.route(enemy.position, player.position)
                if planner is None
                else planner.route_for(
                    enemy.position, player.position, variant=enemy.entity_id
                )
            )
        return self._cached_route

    @staticmethod
    def _cells(surface, camera, navigation):
        cell_size = navigation.cell_size
        left = max(0, int((-camera[0]) // cell_size) - 1)
        right = min(
            navigation.columns - 1,
            int((surface.get_width() - camera[0]) // cell_size) + 1,
        )
        top = max(0, int((-camera[1]) // cell_size) - 1)
        bottom = min(
            navigation.rows - 1,
            int((surface.get_height() - camera[1]) // cell_size) + 1,
        )
        for cell_x in range(left, right + 1):
            for cell_y in range(top, bottom + 1):
                rect = pygame.Rect(
                    cell_x * cell_size + camera[0],
                    cell_y * cell_size + camera[1],
                    cell_size,
                    cell_size,
                )
                colour = (60, 210, 120, 24) if navigation.walkable(
                    (cell_x, cell_y)
                ) else (240, 60, 70, 52)
                pygame.draw.rect(surface, colour, rect)
                pygame.draw.rect(surface, (100, 175, 205, 80), rect, 1)

    @staticmethod
    def _goal(surface, camera, navigation):
        if navigation.goal is None:
            return
        cell_x, cell_y = navigation.goal
        rect = pygame.Rect(
            cell_x * navigation.cell_size + camera[0],
            cell_y * navigation.cell_size + camera[1],
            navigation.cell_size,
            navigation.cell_size,
        )
        pygame.draw.rect(surface, (255, 220, 50, 220), rect, 3)

    @staticmethod
    def _draw_route(surface, camera, route):
        if route is None or len(route.waypoints) < 2:
            return
        points = tuple(
            (round(point[0] + camera[0]), round(point[1] + camera[1]))
            for point in route.waypoints
        )
        pygame.draw.lines(surface, (70, 240, 255, 230), False, points, 3)
        for point in points:
            pygame.draw.circle(surface, (70, 240, 255, 230), point, 5)

    @staticmethod
    def _stuck(surface, snapshot, camera):
        stuck = set(getattr(snapshot.mode_status, "stuck_enemy_ids", ()))
        for entity in snapshot.entities:
            if entity.entity_id not in stuck or entity.position is None:
                continue
            centre = round(entity.position[0] + camera[0]), round(
                entity.position[1] + camera[1]
            )
            pygame.draw.circle(surface, (255, 50, 220, 230), centre, 32, 3)

    @staticmethod
    def _summary(surface, status, navigation, route):
        font = pygame.font.Font(None, 22)
        route_status = "-" if route is None else route.status.upper()
        waypoint_count = 0 if route is None else len(route.waypoints)
        lines = (
            "NAV DEBUG (N TO CLOSE)",
            f"CELL {navigation.cell_size}  GOAL {navigation.goal or '-'}",
            f"REACHABLE {len(navigation._directions)}  "
            f"STUCK {len(getattr(status, 'stuck_enemy_ids', ()))}",
            f"ROUTE {route_status} WP {waypoint_count}",
            f"ROUTE CACHE req={getattr(status, 'navigation_route_requests', 0)} "
            f"hit={getattr(status, 'navigation_route_cache_hits', 0)}",
        )
        panel = pygame.Rect(12, 188, 280, 102)
        pygame.draw.rect(surface, (8, 12, 16), panel)
        pygame.draw.rect(surface, (255, 220, 50), panel, 2)
        for index, line in enumerate(lines):
            text = font.render(line, True, (230, 235, 238))
            surface.blit(text, (20, 194 + index * 19))


def _distance(first, second):
    return (first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2
