"""A Match owns one isolated, disposable authoritative simulation."""

import ast
from pathlib import Path

import pytest

from shooter.map_definition import MapDefinition, MapRequirements
from shooter.match import (
    CREATED,
    DISPOSED,
    RUNNING,
    IncompatibleMatchError,
    Match,
    MatchDisposedError,
)
from shooter.match_configuration import (
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.spatial import Box, Transform


def resolved_match(*, seed=17, capabilities=("bounds",), required=("bounds",)):
    definition = MapDefinition(
        "arena",
        "Arena",
        "Maps/arena.tmx",
        (1000, 800),
        capabilities=frozenset(capabilities),
    )
    mode = ModeDescriptor(
        "test_mode",
        "Test Mode",
        "A test mode",
        MapRequirements(capabilities=frozenset(required)),
    )
    return MatchConfigurationResolver(
        ModeCatalog((mode,)), MapCatalog((definition,))
    ).resolve(MatchConfiguration(mode.mode_id, definition.map_id, seed))


class RecordingMode:
    def __init__(self):
        self.calls = []

    def start(self, match):
        self.calls.append(("start", match.tick))

    def advance(self, match, commands, dt):
        self.calls.append(("advance", match.tick, commands, dt))

    def dispose(self, match):
        self.calls.append(("dispose", match.tick))


def test_match_owns_state_and_drives_a_mode_through_its_lifecycle():
    mode = RecordingMode()
    match = Match(resolved_match())

    assert match.state == CREATED
    match.start(mode)
    match.advance(0.25, ("move",))

    assert match.state == RUNNING
    assert match.tick == 1
    match.dispose()
    assert mode.calls == [
        ("start", 0),
        ("advance", 1, ("move",), 0.25),
        ("dispose", 1),
    ]


def test_named_random_streams_are_reproducible_and_independent():
    first = Match(resolved_match(seed=90210))
    second = Match(resolved_match(seed=90210))

    first.random_stream("loot").random()
    first_spread = [first.random_stream("spread").random() for _ in range(3)]
    second_spread = [second.random_stream("spread").random() for _ in range(3)]

    assert first_spread == second_spread


def test_dispose_clears_all_match_owned_state_and_rejects_further_use():
    match = Match(resolved_match())
    entity_id = match.entities.register(object())
    match.spatial.attach(entity_id, Transform(10, 20), Box(4, 5))
    match.combat.attach(entity_id, 100)
    match.factions.assign(entity_id, "testers")
    match.random_stream("spawn")

    match.dispose()

    assert match.state == DISPOSED
    assert len(match.entities) == 0
    assert len(match.spatial) == 0
    assert len(match.combat) == 0
    assert len(match.factions) == 0
    assert len(match.events) == 0
    with pytest.raises(MatchDisposedError):
        match.advance()
    with pytest.raises(MatchDisposedError):
        match.random_stream("spawn")


def test_incompatible_configuration_cannot_construct_a_match():
    with pytest.raises(IncompatibleMatchError):
        Match(resolved_match(capabilities=(), required=("bounds",)))


def test_match_module_has_no_direct_pygame_dependency():
    source = Path("shooter/match.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports
