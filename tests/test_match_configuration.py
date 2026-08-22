"""Mode and map selection resolves before match state is constructed."""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from shooter.map_definition import MapDefinition, MapRequirements, SpawnPoint
from shooter.match_configuration import (
    ZOMBIE_SURVIVAL,
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
    UnknownCatalogEntryError,
    default_map_catalog,
    default_mode_catalog,
)


def map_definition(map_id="arena", capabilities=("bounds", "spawns"), spawns=()):
    return MapDefinition(
        map_id,
        map_id.title(),
        f"Maps/{map_id}.tmx",
        (1000, 800),
        capabilities=frozenset(capabilities),
        spawns=tuple(spawns),
    )


def test_catalogs_expose_stable_lightweight_selection_metadata():
    mode = ModeDescriptor("duel", "Duel", "Two teams", MapRequirements())
    definition = map_definition()
    modes = ModeCatalog((mode,))
    maps = MapCatalog((definition,))

    assert modes.descriptors() == (mode,)
    (metadata,) = maps.descriptors()
    assert metadata.map_id == "arena"
    assert metadata.display_name == "Arena"
    assert metadata.size == (1000, 800)
    assert not hasattr(metadata, "presentation_source")


def test_match_configuration_is_immutable_and_contains_primitive_selection_data():
    configuration = MatchConfiguration("duel", "arena", seed=90210)

    with pytest.raises(FrozenInstanceError):
        configuration.seed = 1

    assert configuration == MatchConfiguration("duel", "arena", 90210)


def test_compatible_selection_resolves_mode_and_map_definitions():
    spawns = (
        SpawnPoint("alpha", (100, 100), role="team_a"),
        SpawnPoint("bravo", (900, 700), role="team_b"),
    )
    mode = ModeDescriptor(
        "duel",
        "Duel",
        "Two teams",
        MapRequirements(
            capabilities=frozenset(("bounds", "spawns")),
            spawn_roles=frozenset(("team_a", "team_b")),
        ),
    )
    definition = map_definition(spawns=spawns)
    result = MatchConfigurationResolver(
        ModeCatalog((mode,)), MapCatalog((definition,))
    ).resolve(MatchConfiguration("duel", "arena", 12))

    assert result.compatible is True
    assert result.mode is mode
    assert result.map_definition is definition


def test_incompatible_selection_reports_missing_capabilities_and_roles():
    mode = ModeDescriptor(
        "duel",
        "Duel",
        "Two teams",
        MapRequirements(
            capabilities=frozenset(("bounds", "spawns", "destructibles")),
            spawn_roles=frozenset(("team_a", "team_b")),
        ),
    )
    result = MatchConfigurationResolver(
        ModeCatalog((mode,)), MapCatalog((map_definition(capabilities=("bounds",)),))
    ).resolve(MatchConfiguration("duel", "arena", 12))

    assert result.compatible is False
    assert result.compatibility.missing_capabilities == {"spawns", "destructibles"}
    assert result.compatibility.missing_spawn_roles == {"team_a", "team_b"}


def test_unknown_and_duplicate_catalog_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate catalog id"):
        ModeCatalog(
            (
                ModeDescriptor("duel", "One", ""),
                ModeDescriptor("duel", "Two", ""),
            )
        )
    with pytest.raises(UnknownCatalogEntryError):
        MapCatalog(()).get("missing")


def test_default_survival_and_current_map_are_selectable_during_tmx_migration():
    modes = default_mode_catalog()
    maps = default_map_catalog()
    current = maps.descriptors()[0]

    result = MatchConfigurationResolver(modes, maps).resolve(
        MatchConfiguration(ZOMBIE_SURVIVAL, current.map_id, seed=1)
    )

    assert result.compatible is True


def test_match_configuration_module_has_no_direct_pygame_dependency():
    source = Path("shooter/match_configuration.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports
