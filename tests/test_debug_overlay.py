"""The gameplay HUD is text derived from immutable presentation values."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pygame
import pytest

from shooter.presentation_status import SessionPresentationStatus
from shooter.session import Session
from shooter.ui.debug_overlay import BACKGROUND, DebugOverlay, PANEL
from shooter.ui.equipment_overlay import EquipmentDebugOverlay
from shooter.viewport import Viewport

WINDOW = (1080, 720)


def test_overlay_lines_report_match_player_weapon_and_survival_state(display):
    session = Session(Viewport(WINDOW))
    lines = DebugOverlay().lines(session.snapshot, session.presentation_status)
    text = "\n".join(lines)

    assert "MATCH zombie_survival" in text
    assert f"SEED {session.match.configuration.seed}" in text
    assert f"PLAYER id={session.player_id}" in text
    assert "faction=survivors" in text
    assert f"WEAPON {session.equipped.definition.definition_id}" not in text
    equipment = "\n".join(EquipmentDebugOverlay().lines(session.snapshot))
    assert session.equipped.definition.definition_id in equipment
    assert "CASH 0" in text
    assert "EQUIPMENT grenade=" in text


def test_presentation_status_is_frozen_and_copies_temporary_values(display):
    session = Session(Viewport(WINDOW))
    status = session.presentation_status
    before = status.grenades

    session.grenade_data.grenade_amount -= 1

    assert status.grenades == before
    with pytest.raises(FrozenInstanceError):
        status.notice = "changed"


def test_gameplay_no_longer_constructs_legacy_graphical_hud(display):
    session = Session(Viewport(WINDOW))
    for name in (
        "radar",
        "heads_up_display",
        "health_display",
        "weapon_display",
        "shop_display",
        "mode_status_display",
    ):
        assert not hasattr(session, name)

    session.draw(pygame.Surface(WINDOW), 0.0)


def test_shop_overlay_is_an_immutable_copy_for_the_text_renderer(display):
    session = Session(Viewport(WINDOW))
    session.shopping = True
    session.cash.balance = 600
    status = session.presentation_status

    session.cash.balance = 0

    assert status.shop_offers[0].affordable is True
    assert "SHOP 1:" in "\n".join(DebugOverlay().lines(session.snapshot, status))


def test_debug_overlay_uses_text_and_primitives_without_gameplay_assets(display):
    session = Session(Viewport(WINDOW))
    surface = pygame.Surface(WINDOW, pygame.SRCALPHA)
    DebugOverlay().draw(surface, session.snapshot, session.presentation_status)
    source = Path("shooter/ui/debug_overlay.py").read_text()

    assert surface.get_at((PANEL[0] + 2, PANEL[1] + 2))[:3] == BACKGROUND[:3]
    assert "load_image" not in source
    assert "shooter.assets" not in source


def test_debug_overlay_expands_to_fit_its_longest_status_line(display):
    session = Session(Viewport(WINDOW))
    status = replace(session.presentation_status, notice="X" * 100)
    surface = pygame.Surface(WINDOW, pygame.SRCALPHA)

    DebugOverlay().draw(surface, session.snapshot, status)

    assert surface.get_at((700, PANEL[1] + 2))[:3] == BACKGROUND[:3]


def test_status_type_can_be_constructed_without_pygame_values():
    status = SessionPresentationStatus(1, 2, 3.0, (("wood", 4),))

    assert status.cargo == (("wood", 4),)
