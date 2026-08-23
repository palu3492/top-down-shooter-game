"""The legacy pygame actor adapter consumes explicit neutral positions."""

import ast
import random
from pathlib import Path

import pygame

from shooter import config
from shooter.actor_adapter import LegacyActorFactory, walker_definition
from shooter.actor_creation import ActorCreationRequest
from shooter.entities.zombie import Zombie
from shooter.systems.waves import WaveSystem

WINDOW = (1080, 720)


class NoPlacementRandom:
    def uniform(self, left, right):
        return (left + right) / 2

    def randint(self, left, right):
        raise AssertionError("explicit construction tried to choose a position")


def test_explicit_zombie_position_does_not_use_placement_randomness(display):
    zombie = Zombie(WINDOW, position=(125, 275), rng=NoPlacementRandom())

    assert zombie.get_position() == (125, 275)


def test_factory_can_create_the_same_actor_at_selected_positions(display):
    factory = LegacyActorFactory(random.Random(4))
    definition = walker_definition()

    first = factory.create(
        WINDOW, definition, ActorCreationRequest("walker", (10, 20))
    )
    second = factory.create(
        WINDOW, definition, ActorCreationRequest("walker", (300, 400))
    )

    assert first.get_position() == (10, 20)
    assert second.get_position() == (300, 400)


def test_production_zombie_construction_is_owned_by_actor_adapter():
    construction_sites = []
    for path in Path("shooter").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Zombie"
            ):
                construction_sites.append(path.as_posix())

    assert set(construction_sites) == {"shooter/actor_adapter.py"}


def test_wave_system_constructs_walkers_through_the_actor_factory(display, cash):
    group = pygame.sprite.Group()
    factory = LegacyActorFactory(random.Random(12))
    WaveSystem(WINDOW, group, cash, actor_factory=factory)

    assert len(group) == config.WAVE_BASE
    assert all(zombie.get_position() != (0, 0) for zombie in group)
