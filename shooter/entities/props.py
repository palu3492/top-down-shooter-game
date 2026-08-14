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


class Prop(Interpolated, pygame.sprite.Sprite):
    """A fixture at a world position.

    `reach` is how close the player has to be for it to offer itself. Measured
    from the middle of the prop to the player, so a wide one is not easier to
    reach along its length than across it.
    """

    def __init__(self, sprite, x, y, label="", reach=REACH):
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image(sprite, True)
        self.rect = self.image.get_rect()
        self.prop_x = x
        self.prop_y = y
        self.label = label
        self.reach = reach
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

    def within(self, point):
        """Whether something at this world position is close enough to use it."""
        return math.dist(self.middle, point) <= self.reach

    def update(self, camera_x, camera_y, dt=config.SIM_DT):
        """Nothing happens to a prop. It is here so a group can be stepped
        without knowing what is in it."""
