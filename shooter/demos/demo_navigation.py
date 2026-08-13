"""Cheap obstacle-aware navigation for the fixed-screen 2.5D demo."""

from __future__ import annotations

from collections import deque

import pygame


class FlowField:
    """A periodically rebuilt breadth-first flow field on a small grid."""

    def __init__(self, bounds: pygame.Rect, cell_size: int = 32) -> None:
        self.bounds = bounds.copy()
        self.cell_size = cell_size
        self.cols = (bounds.width + cell_size - 1) // cell_size
        self.rows = (bounds.height + cell_size - 1) // cell_size
        self.blocked: set[tuple[int, int]] = set()
        self.distance: dict[tuple[int, int], int] = {}

    def rebuild(self, obstacles: list[pygame.Rect], target: pygame.Vector2) -> None:
        self.blocked.clear()
        for row in range(self.rows):
            for col in range(self.cols):
                rect = self.cell_rect((col, row)).inflate(-8, -8)
                if any(rect.colliderect(obstacle) for obstacle in obstacles):
                    self.blocked.add((col, row))
        goal = self.cell(target)
        self.blocked.discard(goal)
        self.distance = {goal: 0}
        queue = deque([goal])
        while queue:
            cell = queue.popleft()
            for neighbor in self.neighbors(cell):
                if neighbor in self.blocked or neighbor in self.distance:
                    continue
                self.distance[neighbor] = self.distance[cell] + 1
                queue.append(neighbor)

    def cell(self, position: pygame.Vector2) -> tuple[int, int]:
        return (
            max(
                0,
                min(
                    self.cols - 1, int((position.x - self.bounds.left) / self.cell_size)
                ),
            ),
            max(
                0,
                min(
                    self.rows - 1, int((position.y - self.bounds.top) / self.cell_size)
                ),
            ),
        )

    def cell_rect(self, cell: tuple[int, int]) -> pygame.Rect:
        return pygame.Rect(
            self.bounds.left + cell[0] * self.cell_size,
            self.bounds.top + cell[1] * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def neighbors(self, cell: tuple[int, int]) -> list[tuple[int, int]]:
        col, row = cell
        return [
            (x, y)
            for x, y in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1))
            if 0 <= x < self.cols and 0 <= y < self.rows
        ]

    def direction(
        self, position: pygame.Vector2, target: pygame.Vector2
    ) -> pygame.Vector2:
        current = self.cell(position)
        choices = [c for c in self.neighbors(current) if c in self.distance]
        if not choices:
            return (
                (target - position).normalize()
                if target != position
                else pygame.Vector2()
            )
        best = min(choices, key=lambda cell: self.distance[cell])
        return (pygame.Vector2(self.cell_rect(best).center) - position).normalize()
