"""Things that stand in the world and can be stood next to.

The interaction layer, and deliberately the whole of it. A prop does not move,
does not fight and cannot be shot -- what it can do is be near the player, which
is what `E` acts on.

AT42 builds harvesting on this rather than beside it: a tree is a prop that also
has health and a yield, and a shop is one that does not.
"""

import math
from dataclasses import dataclass

import pygame

from shooter import config
from shooter.assets import load_image
from shooter.render import Interpolated

REACH = 170


@dataclass(frozen=True)
class Yield:
    """What comes out of a thing, and what a whole one is worth.

    A total rather than a rate per swing, which is what makes a better tool
    faster rather than poorer: "two per swing" would mean a sharper axe fells
    the tree in fewer swings and comes away with less wood.
    """

    item: object
    total: int


BAR_HEIGHT = 8
BAR_GAP = 14


class Prop(Interpolated, pygame.sprite.Sprite):
    """A fixture at a world position.

    `reach` is how close the player has to be for it to offer itself. Measured
    from the middle of the prop to the player, so a wide one is not easier to
    reach along its length than across it.
    """

    def __init__(self, art, x, y, label="", reach=REACH, solid=None):
        pygame.sprite.Sprite.__init__(self)
        # A path for art that exists, a `Surface` for art that is drawn in code
        # until it does. Both are shared between props rather than copied.
        self.image = art if isinstance(art, pygame.Surface) else load_image(art, True)
        self.rect = self.image.get_rect()
        self.prop_x = x
        self.prop_y = y
        self.label = label
        self.reach = reach
        self.solid = solid
        self.remember_position()

    @property
    def world_x(self):
        return self.prop_x

    @property
    def world_y(self):
        return self.prop_y

    @property
    def middle(self):
        return (
            self.prop_x + self.rect.width / 2,
            self.prop_y + self.rect.height / 2,
        )

    @property
    def footprint(self):
        """What cannot be walked through, in world coordinates.

        `solid` may be a width/height centred on the picture, or an x/y/width/
        height box measured from its top-left. The latter lets irregular art
        exclude transparent padding without shifting its collision box.
        """
        if self.solid is None:
            return None
        if len(self.solid) == 2:
            box = pygame.Rect(0, 0, *self.solid)
            box.center = self.middle
        else:
            box = pygame.Rect(self.solid)
            box.move_ip(self.prop_x, self.prop_y)
        return box

    def within(self, point):
        """Whether something at this world position is close enough to use it."""
        return math.dist(self.middle, point) <= self.reach

    def update(self, camera_x, camera_y, dt=config.SIM_DT):
        """Nothing happens to a prop. It is here so a group can be stepped
        without knowing what is in it."""


class Harvestable(Prop):
    """A prop with something in it.

    Its health is not damage-until-dead the way a zombie's is -- it is *how much
    is left in the thing*, which is why the yield AT43 mints is proportional to
    the damage dealt rather than to the number of blows. A better axe should
    fell a tree in fewer swings, not come away with less wood.

    `hit` returns the damage that actually landed, which is what a yield rule
    multiplies. Overkill on the last blow is trimmed, so a tree with two health
    left cannot pay out as though it had forty.
    """

    def __init__(
        self,
        art,
        x,
        y,
        health,
        tool=None,
        yields=None,
        damage_art=(),
        fit_damage_art=False,
        **rest,
    ):
        super().__init__(art, x, y, **rest)
        self.fit_damage_art = fit_damage_art
        self.damage_art = tuple(
            self._match_art_footprint(
                art if isinstance(art, pygame.Surface) else load_image(art, True)
            )
            for art in damage_art
        )
        self.full = float(health)
        self.health = float(health)
        self.tool = tool
        self.yields = yields
        self.paid = 0

    def _match_art_footprint(self, art):
        """Put alternate art on the intact art's canvas and ground anchor.

        Damage variants are often exported with the object a few pixels higher
        or lower inside an otherwise equal-sized PNG. Swapping those canvases
        directly makes a stationary prop appear to jump. Keep every state the
        same size and align the visible artwork by its bottom-centre point. Art
        that changes silhouette dramatically can opt into the intact visible
        bounds as well, preventing its footprint from pulsing between frames.
        """
        canvas = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        intact = self.image.get_bounding_rect(min_alpha=1)
        alternate = art.get_bounding_rect(min_alpha=1)
        if intact and alternate:
            if self.fit_damage_art:
                visible = art.subsurface(alternate)
                canvas.blit(pygame.transform.smoothscale(visible, intact.size), intact)
                return canvas
            dx = intact.centerx - alternate.centerx
            dy = intact.bottom - alternate.bottom
        else:
            dx = dy = 0
        canvas.blit(art, (dx, dy))
        return canvas

    def _show_damage(self):
        """Make depletion visible without changing the prop's world position."""
        if not self.damage_art:
            return
        # Variants divide the remaining health evenly across the intact and
        # progressively damaged appearances.
        stages = len(self.damage_art)
        stage = min(int((1.0 - self.left) * (stages + 1)), stages)
        if stage:
            self.image = self.damage_art[stage - 1]

    @property
    def left(self):
        """How much of it remains, nought to one. Its health bar, and later its
        remaining yield."""
        return self.health / self.full if self.full else 0.0

    def worked_by(self, held):
        """Whether what is in hand is the right thing for this."""
        return self.tool is None or held.weapon.id == self.tool

    def health_bar(self, screen, at=None):
        """Only worth drawing once something has been taken out of it.

        The same bar a zombie gets, because it is the same fact: how much of
        this is left. On a tree that also reads as how much wood is still in
        it, which is the point of tying yield to damage.
        """
        x, y = at if at else self.rect.topleft
        width = self.rect.width
        pygame.draw.rect(
            screen, config.HEALTH_GREEN, (x, y - BAR_GAP, width * self.left, BAR_HEIGHT)
        )
        pygame.draw.rect(
            screen, config.HEALTH_GREY, (x, y - BAR_GAP, width, BAR_HEIGHT), 2
        )

    def hit(self, damage, held):
        """Take a blow; report what landed. Nothing lands with the wrong tool."""
        if damage <= 0 or not self.worked_by(held):
            return 0.0
        spent = min(float(damage), self.health)
        self.health -= spent
        if self.health <= 0:
            self.kill()
        else:
            self._show_damage()
        return spent

    def harvest(self, damage, held):
        """Land a blow, and report how many whole items it shook loose.

        Proportional to the damage that actually landed, so the total a thing
        pays out is a property of the thing rather than of how many swings it
        took -- and the last blow cannot pay for more than was left in it,
        because `hit` trims overkill before this ever sees it.
        """
        if not self.hit(damage, held) or self.yields is None:
            return 0
        # Worked out from how much of the thing is gone, not accumulated blow
        # by blow. Fractions added up one swing at a time drift: a tree
        # declared as ten wood paid out nine, because 0.333... + 1.666... is
        # 1.99999999 and the whole part of that is one.
        gone = (self.full - self.health) / self.full
        minted = int(self.yields.total * gone)
        won = minted - self.paid
        self.paid = minted
        return won
