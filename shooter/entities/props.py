"""Things that stand in the world and can be stood next to.

The interaction layer, and deliberately the whole of it. A prop does not move,
does not fight and cannot be shot -- what it can do is be near the player, which
is what `E` acts on.

AT42 builds harvesting on this rather than beside it: a tree is a prop that also
has health and a yield, and a shop is one that does not.
"""

import math

import pygame

from shooter import config
from shooter.assets import load_image
from shooter.render import Interpolated

REACH = 170

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

        Smaller than the picture and `None` for most things: a canopy is drawn
        far wider than the part of a tree you would actually bump into, and a
        footprint the size of the sprite makes a wood feel like a maze.
        """
        if self.solid is None:
            return None
        box = pygame.Rect(0, 0, *self.solid)
        box.center = self.middle
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

    def __init__(self, art, x, y, health, tool=None, **rest):
        super().__init__(art, x, y, **rest)
        self.full = float(health)
        self.health = float(health)
        self.tool = tool

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
        return spent
