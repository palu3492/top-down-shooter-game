"""Shared coarse navigation fields for many actors pursuing one destination."""

from collections import deque
from dataclasses import dataclass, field
import heapq
import math

from shooter.world_collision import Aabb, bounds_of, contains, overlaps

ROUTE_FOUND = "found"
UNREACHABLE = "unreachable"


@dataclass(frozen=True, slots=True)
class NavigationRoute:
    """An immutable waypoint path through a clearance-aware navigation grid."""

    status: str
    cells: tuple[tuple[int, int], ...] = ()
    waypoints: tuple[tuple[float, float], ...] = ()


class NavigationRoutePlanner:
    """Bounded route cache over one immutable navigation surface."""

    def __init__(self, navigation, capacity=512):
        if capacity < 1:
            raise ValueError("capacity must be at least one")
        self.navigation = navigation
        self.capacity = capacity
        self._routes = {}
        self.requests = 0
        self.cache_hits = 0

    def route_for(self, start, destination, variant=0):
        key = (
            self.navigation.cell_at(start),
            self.navigation.cell_at(destination),
            int(variant) % 8,
        )
        self.requests += 1
        route = self._routes.get(key)
        if route is not None:
            self.cache_hits += 1
            return route
        route = self.navigation.route(start, destination, variant=variant)
        if len(self._routes) >= self.capacity:
            self._routes.pop(next(iter(self._routes)))
        self._routes[key] = route
        return route


@dataclass(frozen=True, slots=True)
class FlowField:
    """A reusable static-map field directed toward one world-space destination."""

    size: tuple[int, int]
    cell_size: int
    footprint: tuple[float, float]
    collision: tuple[object, ...]
    playable_areas: tuple[object, ...] = ()
    columns: int = field(init=False)
    rows: int = field(init=False)
    _obstacle_cells: dict[tuple[int, int], list[int]] = field(init=False)
    _directions: dict[tuple[int, int], tuple[int, int]] = field(init=False)
    _costs: dict[tuple[int, int], int] = field(init=False)
    _walkable: dict[tuple[int, int], bool] = field(init=False)
    goal: tuple[int, int] | None = field(init=False)

    def __post_init__(self):
        width, height = self.size
        columns = math.ceil(width / self.cell_size)
        rows = math.ceil(height / self.cell_size)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "rows", rows)
        cells = {}
        for index, obstacle in enumerate(self.collision):
            bounds = bounds_of(obstacle)
            left = max(0, int(bounds.left // self.cell_size))
            right = min(columns - 1, int((bounds.right - 0.0001) // self.cell_size))
            top = max(0, int(bounds.top // self.cell_size))
            bottom = min(rows - 1, int((bounds.bottom - 0.0001) // self.cell_size))
            for cell_x in range(left, right + 1):
                for cell_y in range(top, bottom + 1):
                    cells.setdefault((cell_x, cell_y), []).append(index)
        object.__setattr__(self, "_obstacle_cells", cells)
        object.__setattr__(self, "_directions", {})
        object.__setattr__(self, "_costs", {})
        object.__setattr__(self, "_walkable", {})
        object.__setattr__(self, "goal", None)

    def rebuild(self, destination):
        """Build directions from every reachable cell toward *destination*."""
        goal = self._nearest_walkable(self.cell_at(destination))
        directions = {}
        costs = {}
        if goal is not None:
            queue = deque((goal,))
            directions[goal] = (0, 0)
            costs[goal] = 0
            while queue:
                current = queue.popleft()
                for neighbour in self._reachable_neighbours(current):
                    if neighbour in directions:
                        continue
                    costs[neighbour] = costs[current] + _step_cost(current, neighbour)
                    directions[neighbour] = (
                        current[0] - neighbour[0],
                        current[1] - neighbour[1],
                    )
                    queue.append(neighbour)
        object.__setattr__(self, "goal", goal)
        object.__setattr__(self, "_directions", directions)
        object.__setattr__(self, "_costs", costs)

    def direction_at(self, position):
        return self._directions.get(self.cell_at(position))

    def route(self, start, destination, variant=0):
        """Return a deterministic eight-direction waypoint route, if one exists."""
        first = self._nearest_walkable(self.cell_at(start))
        goal = self._nearest_walkable(self.cell_at(destination))
        if first is None or goal is None:
            return NavigationRoute(UNREACHABLE)
        frontier = [(0, 0, first)]
        costs = {first: 0}
        previous = {}
        sequence = 0
        while frontier:
            _, _, current = heapq.heappop(frontier)
            if current == goal:
                cells = self._reconstruct_route(previous, current)
                return NavigationRoute(ROUTE_FOUND, cells, self._waypoints(cells))
            for neighbour in self._reachable_neighbours(current, variant):
                cost = costs[current] + _step_cost(current, neighbour)
                if cost >= costs.get(neighbour, math.inf):
                    continue
                costs[neighbour] = cost
                previous[neighbour] = current
                sequence += 1
                remaining = _octile_distance(neighbour, goal)
                heapq.heappush(frontier, (cost + remaining, sequence, neighbour))
        return NavigationRoute(UNREACHABLE)

    def recovery_direction_at(self, position, actor_id, preferred):
        """Choose a deterministic side-step without abandoning the field."""
        cell = self.cell_at(position)
        cost = self._costs.get(cell)
        if cost is None:
            return preferred
        candidates = [
            (neighbour[0] - cell[0], neighbour[1] - cell[1])
            for neighbour in self._reachable_neighbours(cell)
            if neighbour in self._costs
            and self._costs[neighbour] <= cost + 1
            and (neighbour[0] - cell[0], neighbour[1] - cell[1]) != preferred
        ]
        if not candidates:
            return preferred
        candidates.sort()
        return candidates[int(actor_id) % len(candidates)]

    def cell_at(self, position):
        return (
            min(self.columns - 1, max(0, int(position[0] // self.cell_size))),
            min(self.rows - 1, max(0, int(position[1] // self.cell_size))),
        )

    def cell_centre(self, cell):
        return (
            (cell[0] + 0.5) * self.cell_size,
            (cell[1] + 0.5) * self.cell_size,
        )

    def walkable(self, cell):
        cached = self._walkable.get(cell)
        if cached is not None:
            return cached
        if not (0 <= cell[0] < self.columns and 0 <= cell[1] < self.rows):
            return False
        centre = (
            (cell[0] + 0.5) * self.cell_size,
            (cell[1] + 0.5) * self.cell_size,
        )
        footprint = Aabb(
            centre[0] - self.footprint[0] / 2,
            centre[1] - self.footprint[1] / 2,
            *self.footprint,
        )
        if self.playable_areas and not any(
            contains(area, footprint) for area in self.playable_areas
        ):
            self._walkable[cell] = False
            return False
        result = not any(
            overlaps(footprint, self.collision[index])
            for index in self._obstacle_cells.get(cell, ())
        )
        self._walkable[cell] = result
        return result

    def _nearest_walkable(self, start):
        if self.walkable(start):
            return start
        queue = deque((start,))
        visited = {start}
        while queue:
            current = queue.popleft()
            for neighbour in self._reachable_neighbours(current):
                if neighbour in visited:
                    continue
                if self.walkable(neighbour):
                    return neighbour
                visited.add(neighbour)
                queue.append(neighbour)
        return None

    @staticmethod
    def _neighbours(cell):
        x, y = cell
        return (
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
            (x - 1, y - 1),
            (x - 1, y + 1),
            (x + 1, y - 1),
            (x + 1, y + 1),
        )

    def _reachable_neighbours(self, cell, variant=0):
        neighbours = self._neighbours(cell)
        offset = int(variant) % len(neighbours)
        ordered = (*neighbours[offset:], *neighbours[:offset])
        for neighbour in ordered:
            delta_x, delta_y = neighbour[0] - cell[0], neighbour[1] - cell[1]
            if not self.walkable(neighbour):
                continue
            if delta_x and delta_y and not (
                self.walkable((cell[0] + delta_x, cell[1]))
                and self.walkable((cell[0], cell[1] + delta_y))
            ):
                continue
            yield neighbour

    def _waypoints(self, cells):
        if len(cells) < 2:
            return tuple(self.cell_centre(cell) for cell in cells)
        corners = [cells[0]]
        previous_direction = None
        for index, cell in enumerate(cells[1:], 1):
            direction = cell[0] - cells[index - 1][0], cell[1] - cells[index - 1][1]
            if previous_direction is not None and direction != previous_direction:
                corners.append(cells[index - 1])
            previous_direction = direction
        corners.append(cells[-1])
        return tuple(self.cell_centre(cell) for cell in corners)

    @staticmethod
    def _reconstruct_route(previous, current):
        cells = [current]
        while current in previous:
            current = previous[current]
            cells.append(current)
        return tuple(reversed(cells))


def _step_cost(first, second):
    return math.sqrt(2) if first[0] != second[0] and first[1] != second[1] else 1


def _octile_distance(first, second):
    horizontal, vertical = abs(first[0] - second[0]), abs(first[1] - second[1])
    return max(horizontal, vertical) + (math.sqrt(2) - 1) * min(horizontal, vertical)
