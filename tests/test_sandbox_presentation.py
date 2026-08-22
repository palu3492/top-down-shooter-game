"""Sandbox reuses the snapshot-only placeholder presentation."""

from pathlib import Path

import pygame

from shooter.map_definition import MapDefinition, SpawnPoint
from shooter.match import Match
from shooter.match_configuration import (
    SANDBOX,
    MapCatalog,
    MatchConfiguration,
    MatchConfigurationResolver,
    default_mode_catalog,
)
from shooter.modes.sandbox import AttackActor, MoveActor, SandboxMode
from shooter.ui.debug_overlay import DebugOverlay
from shooter.ui.placeholder_world import PLAYER
from shooter.ui.snapshot_presentation import (
    EMPTY_PRESENTATION_STATUS,
    SnapshotPresentation,
)


def sandbox():
    definition = MapDefinition(
        "arena",
        "Arena",
        "unused.tmx",
        (800, 600),
        capabilities=frozenset(("bounds",)),
    )
    resolved = MatchConfigurationResolver(
        default_mode_catalog(), MapCatalog((definition,))
    ).resolve(MatchConfiguration(SANDBOX, "arena", 23))
    match = Match(resolved)
    mode = SandboxMode(
        spawn_sources=(
            SpawnPoint(
                "red",
                (300, 300),
                role="player",
                faction="red",
                actor_kind="soldier",
            ),
            SpawnPoint(
                "blue",
                (500, 300),
                role="player",
                faction="blue",
                actor_kind="soldier",
            ),
        )
    )
    match.start(mode)
    return match, mode


def test_debug_overlay_formats_sandbox_status_without_survival_fields():
    match, _mode = sandbox()
    match.advance(0.5)

    text = "\n".join(
        DebugOverlay().lines(
            match.snapshot(),
            EMPTY_PRESENTATION_STATUS,
        )
    )

    assert "MODE Sandbox" in text
    assert "ELAPSED 0.5s" in text
    assert "STEPS 1" in text
    assert "ACTORS 2" in text
    assert "WAVE" not in text


def test_snapshot_presenter_draws_sandbox_without_advancing_authoritative_state(
    display,
):
    match, mode = sandbox()
    red = mode.actor_ids["red"]
    blue = mode.actor_ids["blue"]
    match.advance(0.25, (MoveActor(red, (1, 0)), AttackActor(red, blue, 20)))
    snapshot = match.snapshot()
    surface = pygame.Surface((800, 600))
    before = (match.tick, match.spatial.get(red), match.combat.get(blue))

    SnapshotPresentation().draw(surface, snapshot)

    assert surface.get_at((340, 300))[:3] == PLAYER.colour
    assert surface.get_at((500, 300))[:3] == PLAYER.colour
    assert (match.tick, match.spatial.get(red), match.combat.get(blue)) == before


def test_snapshot_presenter_has_no_session_or_mode_dependency():
    source = Path("shooter/ui/snapshot_presentation.py").read_text()

    assert "shooter.session" not in source
    assert "shooter.modes" not in source
