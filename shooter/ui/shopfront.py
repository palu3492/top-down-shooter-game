"""The gun stand, drawn over a game that is still running.

Not a scene. A scene on top of gameplay stops the fixed step -- that is what
pausing *is* -- and standing still to shop is supposed to cost the player
something. So this is an overlay the session draws, and the wave keeps coming
while it is open.

That is also why it is worked by the number keys rather than the mouse: aiming
at a menu with zombies closing in is a different game.
"""

import pygame

from shooter import config
from shooter.systems import shop
from shooter.ui.anchor import CENTRE, TOP, inside, place

PANEL_SIZE = (420, 250)
PANEL_INSET = (0, 90)
BACKGROUND = (18, 22, 14)
BORDER = (120, 150, 90)
DIM = (150, 150, 150)
AFFORDABLE = (200, 235, 160)

TITLE_AT = (20, 14)
FIRST_ROW = 56
ROW_HEIGHT = 34
ROW_AT = 20
PRICE_AT = 300
SAYS_AT = 208

PROMPT_TOP = 150

SAYS = {
    shop.BOUGHT: "bought",
    shop.REFILLED: "ammunition topped up",
    shop.TOO_POOR: "not enough coins",
    shop.NO_ROOM: "no slot free",
    shop.STOCKED: "already full",
}


def prompt(screen, window, label):
    """What standing next to something says before you press anything."""
    text = pygame.font.Font(None, 30).render(f"[E]  {label}", True, config.WHITE)
    screen.blit(text, (window[0] / 2 - text.get_width() / 2, PROMPT_TOP))


class ShopFront:
    """Draws the stock, what each line costs, and what just happened."""

    def __init__(self, window):
        self.window = window

    def draw(self, screen, cash, carried, says=None):
        panel = place(PANEL_SIZE, self.window, CENTRE, TOP, PANEL_INSET)
        pygame.draw.rect(screen, BACKGROUND, panel)
        pygame.draw.rect(screen, BORDER, panel, 3)

        self._write(screen, inside(panel, TITLE_AT), "GUN STAND", 34)

        for index, offer in enumerate(shop.STOCK):
            top = FIRST_ROW + index * ROW_HEIGHT
            price = shop.price_of(offer, carried)
            colour = AFFORDABLE if cash.cash_amount >= price else DIM
            owned = " (ammo)" if shop.carrying(carried, offer) else ""
            self._write(
                screen,
                inside(panel, (ROW_AT, top)),
                f"[{index + 1}]  {offer.name}{owned}",
                28,
                colour,
            )
            self._write(screen, inside(panel, (PRICE_AT, top)), f"${price}", 28, colour)

        self._write(
            screen,
            inside(panel, (ROW_AT, SAYS_AT)),
            SAYS.get(says, "[E] to leave"),
            26,
            DIM if says is None else config.WHITE,
        )

    def _write(self, screen, at, message, size, colour=config.WHITE):
        screen.blit(pygame.font.Font(None, size).render(message, True, colour), at)
