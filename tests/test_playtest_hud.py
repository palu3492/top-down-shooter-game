"""Temporary playtest HUD reads immutable snapshots only."""

import pygame

from shooter.session import Session
from shooter.ui.playtest_hud import PlaytestHud
from shooter.viewport import Viewport


def test_playtest_hud_draws_top_panels_and_three_bottom_equipment_slots(display):
    surface = pygame.Surface((1080, 720), pygame.SRCALPHA)
    session = Session(Viewport((1080, 720)))

    PlaytestHud().draw(surface, session.snapshot)

    assert surface.get_at((540, 12))[:3] != (0, 0, 0)
    assert surface.get_at((1000, 12))[:3] != (0, 0, 0)
    assert surface.get_at((540, 700))[:3] != (0, 0, 0)
