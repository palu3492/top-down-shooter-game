"""Shared spawn orchestration keeps mode rules out of placement and factories."""

import random
from types import SimpleNamespace

import pygame

from shooter import config
from shooter.actor_adapter import LegacyActorFactory, walker_definition
from shooter.actor_creation import ActorCreationResult
from shooter.map_definition import SpawnPoint, SpawnRegion
from shooter.spawn_selection import (
    NO_VALID_POSITION,
    PlacementConstraints,
    SpawnQuery,
)
from shooter.spawn_service import (
    LEGACY_VISIBLE_RING,
    SpawnActorRequest,
    SpawnService,
)
from shooter.systems.waves import WaveSystem
from shooter.world_collision import Aabb

WINDOW = (1080, 720)


class RecordingActorFactory:
    def __init__(self):
        self.requests = []

    def create(self, window, definition, request):
        self.requests.append((window, definition, request))
        return ActorCreationResult(
            definition.definition_id,
            definition.actor_kind,
            definition.faction,
            request.position,
            definition.max_health,
            definition.collision_size,
            definition.movement_speed,
        )


def request(count=1, constraints=None, fallback=None):
    return SpawnActorRequest(
        walker_definition(),
        SpawnQuery(role="enemy"),
        constraints or PlacementConstraints(),
        count,
        fallback,
    )


def test_authored_spawn_selection_flows_into_actor_creation_request():
    factory = RecordingActorFactory()
    service = SpawnService(factory, random.Random(3))
    source = SpawnPoint("north", (400, 500), role="enemy")

    result = service.spawn(request(), (source,), WINDOW)

    assert result.complete is True
    assert result.actors[0].position == (400, 500)
    assert factory.requests[0][2].position == (400, 500)


def test_named_legacy_ring_fallback_is_used_only_when_sources_are_missing():
    factory = RecordingActorFactory()
    service = SpawnService(factory, random.Random(5))
    visible = SimpleNamespace(left=1000, top=1000, width=1080, height=720)

    result = service.spawn(
        request(fallback=LEGACY_VISIBLE_RING), (), WINDOW, visible
    )

    assert result.complete is True
    assert result.actors[0].position != (0, 0)


def test_invalid_authored_sources_fail_instead_of_falling_back():
    factory = RecordingActorFactory()
    service = SpawnService(factory, random.Random(2))
    source = SpawnPoint("blocked", (50, 50), role="enemy")
    constraints = PlacementConstraints(collision=(Aabb(0, 0, 100, 100),))

    result = service.spawn(
        request(constraints=constraints, fallback=LEGACY_VISIBLE_RING),
        (source,),
        WINDOW,
    )

    assert result.actors == ()
    assert result.failures[0].reason == NO_VALID_POSITION
    assert factory.requests == []


def test_survival_wave_uses_authored_enemy_region_when_available(display, cash):
    group = pygame.sprite.Group()
    source = SpawnRegion("yard", Aabb(1500, 1500, 500, 500), role="enemy")
    factory = LegacyActorFactory(random.Random(10))
    rules = WaveSystem(
        WINDOW,
        group,
        cash,
        actor_factory=factory,
        spawn_sources=(source,),
    )

    assert len(group) == config.WAVE_BASE
    assert rules.last_spawn_result.complete is True
    assert all(1500 <= zombie.world_x <= 2000 for zombie in group)
    assert all(1500 <= zombie.world_y <= 2000 for zombie in group)
