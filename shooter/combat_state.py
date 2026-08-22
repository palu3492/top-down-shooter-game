"""Pygame-independent health and optional armor state."""

from dataclasses import dataclass, replace

from shooter.world_registry import EntityId


@dataclass(frozen=True, slots=True)
class VitalState:
    health: float
    max_health: float
    armor: float = 0.0
    max_armor: float = 0.0

    @property
    def alive(self):
        return self.health > 0

    @property
    def depleted(self):
        return not self.alive


@dataclass(frozen=True, slots=True)
class Depletion:
    before: VitalState
    after: VitalState
    requested: float
    absorbed: float
    health_lost: float


class CombatStateStore:
    def __init__(self):
        self._states = {}

    def attach(
        self,
        entity_id: EntityId,
        max_health,
        *,
        health=None,
        armor=0.0,
        max_armor=None,
    ):
        if entity_id in self._states:
            raise ValueError(f"entity {entity_id} already has combat state")
        if max_health <= 0:
            raise ValueError("max_health must be positive")
        armor_limit = armor if max_armor is None else max_armor
        state = VitalState(
            health=max(0.0, min(max_health, max_health if health is None else health)),
            max_health=float(max_health),
            armor=max(0.0, min(armor_limit, armor)),
            max_armor=max(0.0, float(armor_limit)),
        )
        self._states[entity_id] = state
        return state

    def get(self, entity_id: EntityId):
        return self._states[entity_id]

    def deplete(self, entity_id: EntityId, amount):
        if amount < 0:
            raise ValueError("depletion amount cannot be negative")
        before = self.get(entity_id)
        absorbed = min(before.armor, amount)
        health_lost = min(before.health, amount - absorbed)
        after = replace(
            before,
            armor=before.armor - absorbed,
            health=before.health - health_lost,
        )
        self._states[entity_id] = after
        return Depletion(before, after, amount, absorbed, health_lost)

    def restore(self, entity_id: EntityId, health=0.0, armor=0.0):
        if health < 0 or armor < 0:
            raise ValueError("restoration amounts cannot be negative")
        before = self.get(entity_id)
        after = replace(
            before,
            health=min(before.max_health, before.health + health),
            armor=min(before.max_armor, before.armor + armor),
        )
        self._states[entity_id] = after
        return after

    def synchronize(self, entity_id: EntityId, health, armor=None):
        """Temporary bridge from legacy actor-owned values during migration."""
        before = self.get(entity_id)
        after = replace(
            before,
            health=max(0.0, min(before.max_health, health)),
            armor=(
                before.armor
                if armor is None
                else max(0.0, min(before.max_armor, armor))
            ),
        )
        self._states[entity_id] = after
        return after

    def remove(self, entity_id: EntityId):
        return self._states.pop(entity_id)

    def __contains__(self, entity_id):
        return entity_id in self._states

    def __len__(self):
        return len(self._states)

    def clear(self):
        self._states.clear()
