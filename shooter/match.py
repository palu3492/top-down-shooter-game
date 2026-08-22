"""Authoritative match-scoped simulation ownership and lifecycle."""

import hashlib
import random
from typing import TYPE_CHECKING

from shooter.combat_state import CombatStateStore
from shooter.damage import DamageService, FactionStore, RelationshipPolicy
from shooter.domain_events import EventQueue
from shooter.match_configuration import (
    ZOMBIE_SURVIVAL,
    MatchConfiguration,
    MapCatalog,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.map_definition import MapRequirements
from shooter.spatial import SpatialStore
from shooter.world_registry import WorldRegistry

if TYPE_CHECKING:
    from shooter.modes.contract import GameMode

CREATED = "created"
RUNNING = "running"
DISPOSED = "disposed"


class IncompatibleMatchError(ValueError):
    pass


class MatchDisposedError(RuntimeError):
    pass


class Match:
    def __init__(self, resolved, relationships=None):
        if not resolved.compatible:
            raise IncompatibleMatchError(resolved.compatibility)
        self.resolved = resolved
        self.configuration = resolved.configuration
        self.map_definition = resolved.map_definition
        self.mode_descriptor = resolved.mode
        self.state = CREATED
        self.tick = 0
        self.mode = None
        self.events = EventQueue()
        self.entities = WorldRegistry(self.events)
        self.spatial = SpatialStore()
        self.combat = CombatStateStore()
        self.factions = FactionStore()
        self.relationships = relationships or RelationshipPolicy()
        self.damage = DamageService(
            self.combat, self.factions, self.relationships, self.events
        )
        self._random_streams = {}

    def start(self, mode: "GameMode | None" = None):
        self._ensure_available()
        self.mode = mode
        self.state = RUNNING
        if mode is not None:
            mode.start(self)

    def advance(self, dt=0.0, commands=()):
        self._ensure_available()
        if self.state == CREATED:
            self.start()
        self.tick += 1
        if self.mode is not None:
            self.mode.advance(self, tuple(commands), dt)

    def random_stream(self, name):
        self._ensure_available()
        if name not in self._random_streams:
            material = f"{self.configuration.seed}:{name}".encode()
            seed = int.from_bytes(hashlib.blake2b(material, digest_size=16).digest())
            self._random_streams[name] = random.Random(seed)
        return self._random_streams[name]

    def dispose(self):
        if self.state == DISPOSED:
            return
        if self.mode is not None:
            self.mode.dispose(self)
        self.events.clear()
        self.entities.clear()
        self.spatial.clear()
        self.combat.clear()
        self.factions.clear()
        self._random_streams.clear()
        self.mode = None
        self.state = DISPOSED

    def _ensure_available(self):
        if self.state == DISPOSED:
            raise MatchDisposedError("match has been disposed")


def legacy_survival_match(map_definition, seed=0):
    mode = ModeDescriptor(
        ZOMBIE_SURVIVAL,
        "Zombie Survival",
        "Survive escalating enemy waves.",
        MapRequirements(capabilities=frozenset(("bounds",))),
    )
    configuration = MatchConfiguration(ZOMBIE_SURVIVAL, map_definition.map_id, seed)
    resolved = MatchConfigurationResolver(
        ModeCatalog((mode,)), MapCatalog((map_definition,))
    ).resolve(configuration)
    return Match(resolved, RelationshipPolicy((("survivors", "horde"),)))
