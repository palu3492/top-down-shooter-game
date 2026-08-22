"""Pygame-independent authoritative spatial values and storage."""

from dataclasses import dataclass, replace

from shooter.world_registry import EntityId


@dataclass(frozen=True, slots=True)
class Transform:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Box:
    width: float
    height: float
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass(frozen=True, slots=True)
class Circle:
    radius: float
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass(frozen=True, slots=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    def clamp(self, transform: Transform):
        return Transform(
            min(self.right, max(self.left, transform.x)),
            min(self.bottom, max(self.top, transform.y)),
        )


@dataclass(frozen=True, slots=True)
class SpatialState:
    transform: Transform
    collision: Box | Circle | None = None


class SpatialStore:
    """Match-scoped spatial state addressed only through stable entity IDs."""

    def __init__(self):
        self._states = {}

    def attach(self, entity_id: EntityId, transform, collision=None):
        if entity_id in self._states:
            raise ValueError(f"entity {entity_id} already has spatial state")
        state = SpatialState(transform, collision)
        self._states[entity_id] = state
        return state

    def get(self, entity_id: EntityId):
        return self._states[entity_id]

    def move_to(self, entity_id: EntityId, x, y):
        state = replace(self.get(entity_id), transform=Transform(x, y))
        self._states[entity_id] = state
        return state

    def set_collision(self, entity_id: EntityId, collision):
        state = replace(self.get(entity_id), collision=collision)
        self._states[entity_id] = state
        return state

    def remove(self, entity_id: EntityId):
        return self._states.pop(entity_id)

    def __contains__(self, entity_id):
        return entity_id in self._states

    def __len__(self):
        return len(self._states)
