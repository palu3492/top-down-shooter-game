"""Temporary playtest HUD reads immutable snapshots only."""

import pygame

from shooter.session import Session
from shooter.ui.playtest_hud import PlaytestHud
from shooter.viewport import Viewport


def test_playtest_hud_draws_top_panels_and_bottom_equipment_slots(display):
    surface = pygame.Surface((1080, 720), pygame.SRCALPHA)
    session = Session(Viewport((1080, 720)))

    PlaytestHud().draw(surface, session.snapshot)

    assert surface.get_at((540, 12))[:3] != (0, 0, 0)
    assert surface.get_at((1000, 12))[:3] != (0, 0, 0)
    assert surface.get_at((540, 700))[:3] != (0, 0, 0)
    assert surface.get_at((792, 700))[:3] != (0, 0, 0)
    assert surface.get_at((886, 700))[:3] != (0, 0, 0)


def test_playtest_hud_uses_compact_labels_for_explicit_firing_modes():
    from shooter.ui.playtest_hud import _firing_label

    assert _firing_label("semi_automatic") == "SEMI"
    assert _firing_label("automatic") == "AUTO"
    assert _firing_label("burst") == "BURST"
