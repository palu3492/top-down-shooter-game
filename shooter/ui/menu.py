"""The pause menu and the scenes it opens."""

import pygame
import pygame_gui

from shooter import config, session
from shooter.ui import widgets
from shooter.scenes import Scene

RESUME, SETTINGS, DEV, QUIT, BACK = "RESUME", "SETTINGS", "DEV", "QUIT", "BACK"
END_GAME = "END_GAME"
RETRY = "RETRY"
NEXT_LEVEL = "NEXT_LEVEL"

BUTTON_SIZE = (280, 54)
BUTTON_GAP = 14


class MenuScreen(Scene):
    """A screen that is a vertical column of buttons."""

    entries = ()

    def open(self):
        width, height = self.window
        column_height = len(self.entries) * (BUTTON_SIZE[1] + BUTTON_GAP)
        top = (height - column_height) // 2

        self.title_rect = pygame.Rect(0, top - 96, width, 52)
        self.add(widgets.title(self.title_rect, self.title, self.manager))

        self.actions = {}
        for index, (label, action) in enumerate(self.entries):
            rect = pygame.Rect(0, 0, *BUTTON_SIZE)
            rect.centerx = width // 2
            rect.y = top + index * (BUTTON_SIZE[1] + BUTTON_GAP)
            self.actions[self.add(widgets.button(rect, label, self.manager))] = action

    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            return self.actions.get(event.ui_element)
        return None


class PauseScreen(MenuScreen):
    title = "PAUSED"
    opaque = False

    @property
    def entries(self):
        listed = [("RESUME", RESUME), ("SETTINGS", SETTINGS)]
        if config.DEV_TOOLS:
            listed.append(("DEV", DEV))
        listed.append(("END GAME", END_GAME))
        listed.append(("QUIT", QUIT))
        return tuple(listed)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return RESUME
        return super().handle(event)


class ResultScreen(MenuScreen):
    """What happened, and what to do about it.

    Transparent, so the world is still there behind the veil -- where the
    player died is part of what the screen is telling them. It does not
    simulate, which is what stops the zombies closing in on a body.
    """

    opaque = False

    TITLES = ((session.LOST, "YOU DIED"), (session.WON, "LEVEL COMPLETE"))

    def __init__(self, window, manager, outcome=session.LOST, level=None):
        super().__init__(window, manager)
        self.outcome = outcome
        self.level = level

    @property
    def title(self):
        if self.outcome == session.WON and self.level is not None:
            return f"{self.level.title} COMPLETE"
        return dict(self.TITLES).get(self.outcome, "GAME OVER")

    @property
    def entries(self):
        """Winning offers the way onward; losing offers the way back."""
        if self.outcome == session.WON:
            first = ("NEXT LEVEL", NEXT_LEVEL)
        else:
            first = ("RETRY", RETRY)
        return (first, ("MAIN MENU", END_GAME), ("QUIT", QUIT))

    def handle(self, event):
        """Escape does not dismiss this one -- there is nothing to go back to,
        and closing it would leave a finished game running underneath."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return None
        return super().handle(event)
