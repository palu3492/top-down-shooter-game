"""Executable Phase 8 headless-simulation and presentation boundary audit."""

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys

from shooter.map_definition import MapDefinition, MapRequirements
from shooter.match import Match
from shooter.match_configuration import (
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.spatial import Box, Transform


@dataclass(frozen=True, slots=True)
class HeadlessStatus:
    advances: int
    elapsed: float


class HeadlessMode:
    def __init__(self):
        self.advances = 0
        self.elapsed = 0.0
        self.disposed = False

    def start(self, match):
        pass

    def advance(self, match, commands, dt):
        self.advances += 1
        self.elapsed += dt

    def status(self, match):
        return HeadlessStatus(self.advances, self.elapsed)

    def result(self, match):
        return None

    def dispose(self, match):
        self.disposed = True


def headless_match():
    map_definition = MapDefinition(
        "headless_arena",
        "Headless Arena",
        "unused.tmx",
        (800, 600),
        capabilities=frozenset(("bounds",)),
    )
    mode = ModeDescriptor(
        "headless",
        "Headless",
        "Presentation-free test mode",
        MapRequirements(capabilities=frozenset(("bounds",))),
    )
    resolved = MatchConfigurationResolver(
        ModeCatalog((mode,)), MapCatalog((map_definition,))
    ).resolve(MatchConfiguration("headless", "headless_arena", 42))
    return Match(resolved)


def test_match_advances_and_snapshots_without_presentation_objects():
    match = headless_match()
    mode = HeadlessMode()
    match.start(mode)
    actor = match.entities.register(object(), ("actor", "player"))
    match.spatial.attach(actor, Transform(12, 34), Box(20, 24))
    match.combat.attach(actor, 100, health=75)
    match.factions.assign(actor, "players")

    match.advance(0.25, ("move-right",))
    match.advance(0.5)
    snapshot = match.snapshot()

    assert snapshot.tick == 2
    assert snapshot.mode_status == HeadlessStatus(2, 0.75)
    assert snapshot.entity(actor).position == (12, 34)
    assert snapshot.entity(actor).vitality.health == 75
    match.dispose()
    assert mode.disposed is True


def test_fresh_process_can_run_match_while_rejecting_pygame_and_ui_imports():
    program = r'''
import builtins
import json

original_import = builtins.__import__
def headless_import(name, *args, **kwargs):
    if name == "pygame" or name.startswith("pygame."):
        raise AssertionError(f"presentation dependency imported: {name}")
    if name.startswith(("shooter.ui", "shooter.session", "shooter.gameplay")):
        raise AssertionError(f"presentation orchestration imported: {name}")
    return original_import(name, *args, **kwargs)
builtins.__import__ = headless_import

from shooter.map_definition import MapDefinition
from shooter.match import Match
from shooter.match_configuration import (
    MapCatalog, MatchConfiguration, MatchConfigurationResolver,
    ModeCatalog, ModeDescriptor,
)

definition = MapDefinition(
    "arena", "Arena", "unused.tmx", (100, 100),
    capabilities=frozenset(("bounds",)),
)
descriptor = ModeDescriptor("sandbox", "Sandbox", "Headless")
resolved = MatchConfigurationResolver(
    ModeCatalog((descriptor,)), MapCatalog((definition,))
).resolve(MatchConfiguration("sandbox", "arena", 7))
match = Match(resolved)
match.advance(1 / 60)
snapshot = match.snapshot()
print(json.dumps({"state": snapshot.state, "tick": snapshot.tick}))
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"state": "running", "tick": 1}


def test_match_snapshot_boundary_has_no_pygame_ui_or_session_imports():
    modules = (
        "shooter/match.py",
        "shooter/simulation_snapshot.py",
        "shooter/combat_state.py",
        "shooter/damage.py",
        "shooter/domain_events.py",
        "shooter/spatial.py",
        "shooter/world_registry.py",
        "shooter/modes/contract.py",
    )
    forbidden = ("pygame", "shooter.ui", "shooter.session", "shooter.gameplay")

    for filename in modules:
        imports = set()
        for node in ast.walk(ast.parse(Path(filename).read_text())):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        assert not any(
            dependency == prefix or dependency.startswith(f"{prefix}.")
            for dependency in imports
            for prefix in forbidden
        ), filename
