"""Mode/map catalogs and immutable configuration resolved before a match exists."""

from dataclasses import dataclass, field

from shooter.map_definition import (
    MapCapabilityReport,
    MapDefinition,
    MapRequirements,
    current_map_definition,
)

ZOMBIE_SURVIVAL = "zombie_survival"


class UnknownCatalogEntryError(KeyError):
    pass


@dataclass(frozen=True, slots=True)
class ModeDescriptor:
    mode_id: str
    display_name: str
    description: str
    map_requirements: MapRequirements = field(default_factory=MapRequirements)
    hostile_factions: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MapDescriptor:
    map_id: str
    display_name: str
    size: tuple[int, int]
    capabilities: frozenset[str]
    supported_modes: frozenset[str]

    @classmethod
    def from_definition(cls, definition):
        return cls(
            definition.map_id,
            definition.display_name,
            definition.size,
            definition.capabilities,
            definition.supported_modes,
        )


class ModeCatalog:
    def __init__(self, descriptors=()):
        self._entries = _unique(descriptors, lambda item: item.mode_id)

    def get(self, mode_id):
        try:
            return self._entries[mode_id]
        except KeyError as error:
            raise UnknownCatalogEntryError(mode_id) from error

    def descriptors(self):
        return tuple(self._entries.values())


class MapCatalog:
    def __init__(self, definitions=()):
        self._definitions = _unique(definitions, lambda item: item.map_id)

    def get(self, map_id):
        try:
            return self._definitions[map_id]
        except KeyError as error:
            raise UnknownCatalogEntryError(map_id) from error

    def descriptors(self):
        return tuple(
            MapDescriptor.from_definition(definition)
            for definition in self._definitions.values()
        )


@dataclass(frozen=True, slots=True)
class MatchConfiguration:
    mode_id: str
    map_id: str
    seed: int


@dataclass(frozen=True, slots=True)
class ResolvedMatchConfiguration:
    configuration: MatchConfiguration
    mode: ModeDescriptor
    map_definition: MapDefinition
    compatibility: MapCapabilityReport

    @property
    def compatible(self):
        return self.compatibility.compatible


class MatchConfigurationResolver:
    def __init__(self, modes, maps):
        self.modes = modes
        self.maps = maps

    def resolve(self, configuration):
        mode = self.modes.get(configuration.mode_id)
        map_definition = self.maps.get(configuration.map_id)
        return ResolvedMatchConfiguration(
            configuration,
            mode,
            map_definition,
            map_definition.validate(mode.map_requirements),
        )


def default_mode_catalog():
    # Survival can use the named visible-ring fallback until authored enemy
    # spawns are added to the current map, so only world bounds are mandatory.
    return ModeCatalog(
        (
            ModeDescriptor(
                ZOMBIE_SURVIVAL,
                "Zombie Survival",
                "Survive escalating enemy waves.",
                MapRequirements(capabilities=frozenset(("bounds",))),
                (("survivors", "horde"),),
            ),
        )
    )


def default_map_catalog():
    return MapCatalog((current_map_definition(),))


def _unique(items, identify):
    entries = {}
    for item in items:
        item_id = identify(item)
        if item_id in entries:
            raise ValueError(f"duplicate catalog id: {item_id}")
        entries[item_id] = item
    return entries
