"""Attributed attack descriptions independent of pygame and actor classes."""

import math
from dataclasses import dataclass

from shooter.world_registry import EntityId


def damage_at_distance(definition, distance):
    """Return a weapon's data-defined damage after its effective range.

    Targeting decides whether a target is within maximum range. This calculation
    only models the reusable damage falloff within that allowed range.
    """
    maximum = definition.max_range
    effective = definition.effective_range
    if maximum is None or effective is None or maximum <= effective:
        return definition.damage
    progress = (max(0.0, distance) - effective) / (maximum - effective)
    fraction = 1 - (1 - definition.minimum_damage_fraction) * progress
    fraction = min(1.0, max(definition.minimum_damage_fraction, fraction))
    return definition.damage * fraction


@dataclass(frozen=True, slots=True)
class AttackDescription:
    instigator_id: EntityId | None
    weapon_id: str
    attack_kind: str
    damage: float
    origin: tuple[float, float]
    direction: tuple[float, float]
    reach: float | None = None
    arc: float | None = None


class AttackDescriptionService:
    """Describe attacks using injected randomness before presentation adapts them."""

    def create(self, definition, instigator_id, origin, direction, rng):
        if definition.attack_kind == "melee":
            return (
                self._description(definition, instigator_id, origin, direction),
            )
        if definition.attack_kind != "ballistic":
            raise ValueError(f"unknown attack kind: {definition.attack_kind}")
        return tuple(
            self._description(
                definition,
                instigator_id,
                origin,
                self._scatter(direction, definition.spread, rng),
            )
            for _ in range(definition.pellets)
        )

    @staticmethod
    def _description(definition, instigator_id, origin, direction):
        return AttackDescription(
            instigator_id=instigator_id,
            weapon_id=definition.definition_id,
            attack_kind=definition.attack_kind,
            damage=definition.damage,
            origin=tuple(origin),
            direction=tuple(direction),
            reach=definition.reach,
            arc=definition.arc,
        )

    @staticmethod
    def _scatter(direction, spread, rng):
        if not spread:
            return tuple(direction)
        half = math.radians(spread) / 2
        angle = math.atan2(direction[1], direction[0]) + rng.uniform(-half, half)
        reach = math.hypot(*direction)
        return (math.cos(angle) * reach, math.sin(angle) * reach)
