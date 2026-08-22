"""Immutable simulation facts exchanged across match boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shooter.world_registry import EntityId


@dataclass(frozen=True, slots=True)
class EntityRegistered:
    entity_id: EntityId
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityRemoved:
    entity_id: EntityId
    reason: str


@dataclass(frozen=True, slots=True)
class DamageApplied:
    source_id: EntityId | None
    target_id: EntityId
    amount: float
    instigator_id: EntityId | None = None
    weapon_id: str | None = None
    damage_type: str = ""
    tick: int = 0
    absorbed: float = 0.0
    health_damage: float = 0.0


@dataclass(frozen=True, slots=True)
class EntityKilled:
    entity_id: EntityId
    killer_id: EntityId | None
    source_id: EntityId | None = None
    weapon_id: str | None = None
    damage_type: str = ""
    tick: int = 0


class EventQueue:
    """An ordered, match-owned queue—not a global subscription bus."""

    def __init__(self):
        self._pending = []

    def publish(self, event):
        self._pending.append(event)
        return event

    def drain(self):
        pending = tuple(self._pending)
        self._pending.clear()
        return pending

    def __len__(self):
        return len(self._pending)

    def clear(self):
        self._pending.clear()
