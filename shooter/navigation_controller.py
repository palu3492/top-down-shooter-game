"""Headless waypoint following, separate from route planning and movement."""

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class RouteProgress:
    route: object
    waypoint_index: int = 0

    @property
    def complete(self):
        return self.waypoint_index >= len(self.route.waypoints)


class WaypointFollower:
    def __init__(self, arrival_distance=24.0):
        if arrival_distance <= 0:
            raise ValueError("arrival_distance must be positive")
        self.arrival_distance = arrival_distance

    def advance(self, progress, position):
        """Consume reached waypoints and return the next movement direction."""
        index = progress.waypoint_index
        waypoints = progress.route.waypoints
        while index < len(waypoints):
            waypoint = waypoints[index]
            if math.dist(position, waypoint) > self.arrival_distance:
                break
            index += 1
        updated = RouteProgress(progress.route, index)
        if updated.complete:
            return updated, (0.0, 0.0)
        waypoint = waypoints[index]
        dx, dy = waypoint[0] - position[0], waypoint[1] - position[1]
        length = math.hypot(dx, dy)
        return updated, (dx / length, dy / length)
