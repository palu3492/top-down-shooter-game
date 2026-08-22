"""Application-owned selection and lifecycle for one active Match."""

from shooter.match import IncompatibleMatchError, Match
from shooter.damage import RelationshipPolicy
from shooter.match_configuration import (
    ZOMBIE_SURVIVAL,
    MatchConfiguration,
    MatchConfigurationResolver,
    default_map_catalog,
    default_mode_catalog,
)


class MatchHost:
    """State that survives navigation but never belongs to a match."""

    def __init__(self, modes=None, maps=None, configuration=None):
        self.modes = default_mode_catalog() if modes is None else modes
        self.maps = default_map_catalog() if maps is None else maps
        first_map = self.maps.descriptors()[0]
        self.configuration = configuration or MatchConfiguration(
            ZOMBIE_SURVIVAL, first_map.map_id, seed=0
        )
        self.active_match = None

    def select(self, configuration):
        resolved = self._resolve(configuration)
        if not resolved.compatible:
            raise IncompatibleMatchError(resolved.compatibility)
        self.configuration = configuration
        return resolved

    def start(self, configuration=None):
        selected = configuration or self.configuration
        resolved = self._resolve(selected)
        if not resolved.compatible:
            raise IncompatibleMatchError(resolved.compatibility)
        self.leave()
        self.configuration = selected
        relationships = RelationshipPolicy(resolved.mode.hostile_factions)
        self.active_match = Match(resolved, relationships)
        return self.active_match

    def leave(self):
        if self.active_match is not None:
            self.active_match.dispose()
            self.active_match = None

    def _resolve(self, configuration):
        return MatchConfigurationResolver(self.modes, self.maps).resolve(configuration)
