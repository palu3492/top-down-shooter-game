"""Immutable Zombie Survival wave composition and scaling values."""

from dataclasses import dataclass

from shooter.actor_creation import ActorDefinition


@dataclass(frozen=True, slots=True)
class EnemyWaveRule:
    actor: ActorDefinition
    base_count: int
    growth: int = 0
    exponent: int = 1

    def __post_init__(self):
        if self.base_count < 0 or self.growth < 0 or self.exponent < 1:
            raise ValueError("wave counts and growth must be non-negative")

    def count_for(self, wave):
        if wave < 1:
            raise ValueError("wave numbers start at one")
        return self.base_count + self.growth * (wave - 1) ** self.exponent


@dataclass(frozen=True, slots=True)
class SurvivalWavePlan:
    entries: tuple[EnemyWaveRule, ...]
    preparation_seconds: float

    def __post_init__(self):
        if self.preparation_seconds < 0:
            raise ValueError("preparation_seconds cannot be negative")
        identifiers = tuple(entry.actor.definition_id for entry in self.entries)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("wave entries require unique actor definitions")

    def composition(self, wave):
        return tuple(
            (entry.actor.definition_id, entry.count_for(wave))
            for entry in self.entries
            if entry.count_for(wave) > 0
        )
