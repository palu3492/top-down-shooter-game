"""Pygame actor creation adapted from neutral definitions and requests."""

import random

from shooter import config
from shooter.actor_creation import (
    ActorCreationRequest,
    ActorCreationService,
    ActorDefinition,
)
from shooter.entities.zombie import Zombie, spawn_margin

WALKER_ID = "walker"


def walker_definition():
    return ActorDefinition(
        definition_id=WALKER_ID,
        actor_kind="walker",
        faction="horde",
        max_health=config.ZOMBIE_HEALTH,
        collision_size=tuple(config.ZOMBIE_SIZE),
        movement_speed=config.ZOMBIE_SPEED,
    )


class LegacyActorFactory:
    def __init__(self, rng=None):
        self.rng = random if rng is None else rng
        self.creation = ActorCreationService()

    def spawn_walker(self, window, visible=None):
        definition = walker_definition()
        position = legacy_ring_position(
            window,
            visible,
            spawn_margin(definition.movement_speed),
            self.rng,
        )
        return self.create(
            window,
            definition,
            ActorCreationRequest(definition.definition_id, position),
        )

    def create(self, window, definition, request):
        state = self.creation.create(definition, request)
        if state.actor_kind != "walker":
            raise ValueError(f"unsupported legacy actor kind: {state.actor_kind}")
        return Zombie(window, position=state.position, rng=self.rng)


def legacy_ring_position(window, visible, margin, rng):
    if visible is None:
        left, top, width, height = 0, 0, window[0], window[1]
    else:
        left, top = visible.left, visible.top
        width, height = visible.width, visible.height
    right, bottom = left + width, top + height
    side = rng.randint(1, 4)
    if side == 1:
        return (rng.randint(left, right), top - margin)
    if side == 2:
        return (rng.randint(left, right), bottom + margin)
    if side == 3:
        return (left - margin, rng.randint(top, bottom))
    return (right + margin, rng.randint(top, bottom))
