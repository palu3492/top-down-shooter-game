"""Shared orchestration from semantic spawn requests to constructed actors."""

from dataclasses import dataclass, replace

from shooter import config
from shooter.actor_creation import ActorCreationRequest, ActorDefinition
from shooter.spawn_fallback import visible_ring_position
from shooter.spawn_selection import (
    NO_SOURCES,
    PlacementConstraints,
    SpawnQuery,
    SpawnSelector,
)

LEGACY_VISIBLE_RING = "legacy_visible_ring"


@dataclass(frozen=True, slots=True)
class SpawnActorRequest:
    definition: ActorDefinition
    query: SpawnQuery
    constraints: PlacementConstraints
    count: int
    fallback_policy: str | None = None


@dataclass(frozen=True, slots=True)
class SpawnFailure:
    index: int
    reason: str


@dataclass(frozen=True, slots=True)
class SpawnBatchResult:
    actors: tuple[object, ...]
    failures: tuple[SpawnFailure, ...]

    @property
    def complete(self):
        return not self.failures


class SpawnService:
    def __init__(self, actor_factory, rng, selector=None):
        self.actor_factory = actor_factory
        self.rng = rng
        self.selector = selector or SpawnSelector()

    def spawn(self, request, sources, window, visible=None):
        actors = []
        failures = []
        occupied = list(request.constraints.occupied)
        for index in range(max(0, request.count)):
            constraints = replace(request.constraints, occupied=tuple(occupied))
            selected = self.selector.select(
                sources, request.query, constraints, self.rng
            )
            position = selected.position
            if (
                position is None
                and selected.reason == NO_SOURCES
                and request.fallback_policy == LEGACY_VISIBLE_RING
            ):
                position = visible_ring_position(
                    window,
                    visible,
                    _fallback_margin(request.definition),
                    self.rng,
                )
            if position is None:
                failures.append(SpawnFailure(index, selected.reason))
                continue

            actor = self.actor_factory.create(
                window,
                request.definition,
                ActorCreationRequest(request.definition.definition_id, position),
            )
            actors.append(actor)
            occupied.append(position)
        return SpawnBatchResult(tuple(actors), tuple(failures))


def _fallback_margin(definition):
    return max(
        definition.movement_speed * config.SPAWN_LEAD_SECONDS,
        max(definition.collision_size),
    )
