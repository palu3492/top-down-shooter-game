"""What you are carrying, laid out on the AT22 grid.

A scene rather than an overlay, which is what makes it pause: the gun stand
does not, because standing still to shop is meant to cost something, but
looking at your own pack is not a thing the wave should punish.

Nothing here is a `pygame_gui` widget. The screen is a grid of item slots and a
count in the corner of each, which is a handful of rectangles -- and the slots
have to be rebuilt whenever the pack changes, which widgets would make heavier
rather than lighter.
"""

import math

import pygame

from shooter import config, weapons
from shooter.assets import load_image
from shooter.scenes import Scene
from shooter.systems import world
from shooter.ui.layout import Grid
from shooter.ui.menu import BACK

PADDING = 60
TITLE_HEIGHT = 54
CAPTION_HEIGHT = 30
HINT_HEIGHT = 30
SLOT = 92
SMALLEST_SLOT = 44
SLOT_GAP = 10
BACKING = 44

PANEL = (16, 20, 12)
SLOT_BACK = (26, 32, 20)
BORDER = (120, 150, 90)
EMPTY = (52, 60, 44)
FILLED = (86, 108, 68)
HELD = (196, 232, 150)
DIM = (150, 156, 140)

HINT = "click a slot to drop it  ·  [1]-[5] equip  ·  [Tab] to close"


def icon(item):
    """A picture for this item, or `None` when there is not one yet.

    Resources have the shape they are drawn with on the ground; weapons have
    their HUD art. Ammunition has neither, and says its name instead.
    """
    if item.id in world.LOOKS:
        return world.LOOKS[item.id]()
    if item.id in weapons.weapon_ids():
        sprite = weapons.weapon(item.id).sprite
        return load_image(sprite, True) if sprite else None
    return None


class BackpackScreen(Scene):
    """Everything the player is carrying, in one place."""

    title = "BACKPACK"
    opaque = False

    def __init__(self, window, manager, session):
        super().__init__(window, manager)
        self.session = session
        self.slots = ()
        self.hands = ()

    def open(self):
        grid = Grid(pygame.Rect((0, 0), tuple(self.window)), padding=PADDING)
        self.width = grid.area.width
        self.gutter = grid.gutter

        # Both runs of slots are sized together, before a single row is handed
        # out. Fitting them one after the other let the weapons take the space
        # the pack then needed, so a bigger backpack overflowed by a few pixels
        # and `open` raised -- which the shell swallows, leaving `Tab` doing
        # visibly nothing. That is the failure this screen exists to prevent.
        spent = TITLE_HEIGHT + 2 * CAPTION_HEIGHT + HINT_HEIGHT + 4 * grid.gutter
        size, per_row = self._fit(
            grid.free_height - spent,
            (len(self.session.carried), self.session.backpack.slots),
        )

        self.title_at = grid.row(TITLE_HEIGHT).rest()
        self.hands_caption = grid.row(CAPTION_HEIGHT).rest()
        self.hands = self._boxes(grid, len(self.session.carried), size, per_row)
        self.pack_caption = grid.row(CAPTION_HEIGHT).rest()
        self.slots = self._boxes(grid, self.session.backpack.slots, size, per_row)
        self.hint_at = grid.row(HINT_HEIGHT).rest()

        # A backing, not just the veil: the wave banner and the radar are drawn
        # underneath and were reading as part of the pack.
        self.panel = (
            pygame.Rect(0, 0, 0, 0)
            .unionall([self.title_at, self.hint_at, *self.slots, *self.hands])
            .inflate(BACKING, BACKING)
        )

    def _fit(self, room, counts):
        """One slot size that gets every run of them into the room there is.

        Shared between the two runs so they match, and chosen before anything
        is laid out so neither can starve the other.
        """
        room = max(1, room)
        for size in range(SLOT, SMALLEST_SLOT - 1, -8):
            per_row = max(1, self.width // (size + SLOT_GAP))
            rows = sum(math.ceil(max(1, count) / per_row) for count in counts)
            if rows * (size + SLOT_GAP + self.gutter) <= room:
                return size, per_row
        return SMALLEST_SLOT, max(1, self.width // (SMALLEST_SLOT + SLOT_GAP))

    def _boxes(self, grid, count, size, per_row):
        """A run of square slots, wrapped onto as many rows as it takes."""
        made = []
        for start in range(0, max(1, count), per_row):
            row = grid.row(size + SLOT_GAP).rest()
            for column in range(min(per_row, count - start)):
                made.append(
                    pygame.Rect(
                        row.left + column * (size + SLOT_GAP), row.top, size, size
                    )
                )
        return tuple(made)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                return BACK
            self.session.handle(event)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._clicked(event.pos)
        return None

    def _clicked(self, at):
        for box, stack in zip(self.slots, list(self.session.backpack), strict=False):
            if box.collidepoint(at):
                self.session.drop(stack.item, stack.count)
                return
        for box, index in zip(
            self.hands, range(len(self.session.carried)), strict=False
        ):
            if box.collidepoint(at):
                self.session.equip_slot(index)
                return

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface, alpha):
        super().draw(surface, alpha)
        pygame.draw.rect(surface, PANEL, self.panel)
        pygame.draw.rect(surface, BORDER, self.panel, 2)
        self._write(surface, self.title_at.topleft, self.title, 54)

        pack = self.session.backpack
        self._write(surface, self.hands_caption.topleft, "IN HAND", 30, DIM)
        for box, held in zip(self.hands, self.session.carried, strict=False):
            self._slot(
                surface,
                box,
                icon(held.weapon.item),
                held.weapon.name,
                self._rounds(held),
                lit=held is self.session.equipped,
            )

        used = f"PACK   {len(pack)} of {pack.slots} slots"
        self._write(surface, self.pack_caption.topleft, used, 30, DIM)
        for box, stack in zip(self.slots, list(pack), strict=False):
            self._slot(surface, box, icon(stack.item), stack.item.name, stack.count)
        for box in self.slots[len(pack) :]:
            self._slot(surface, box, None, "", None)

        self._write(surface, self.hint_at.topleft, HINT, 26, DIM)

    def _rounds(self, held):
        return None if held.loaded is None else held.loaded + held.reserve

    def _slot(self, surface, box, art, name, count, lit=False):
        pygame.draw.rect(surface, SLOT_BACK, box)
        pygame.draw.rect(surface, HELD if lit else BORDER, box, 3 if lit else 2)
        if art is not None:
            surface.blit(art, art.get_rect(center=box.center))
        elif name:
            self._write(surface, (box.left + 8, box.centery - 10), name[:8].upper(), 24)
        if count is not None:
            self._write(
                surface, (box.left + 8, box.bottom - 24), str(count), 26, FILLED
            )

    def _write(self, surface, at, message, size, colour=config.WHITE):
        surface.blit(pygame.font.Font(None, size).render(message, True, colour), at)
