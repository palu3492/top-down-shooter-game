"""What is lying on the ground waiting to be walked over.

One pickup holds a *count*. Ten wood is one thing to look at and one thing to
draw, never ten things -- and walking over it with room for five takes five and
leaves five behind. That remainder is the whole reason AT37 made `Backpack.add`
report what it took rather than swallowing the difference.
"""

import math

import pygame

from shooter import config
from shooter.render import Interpolated

REACH = 90


class Pickup(Interpolated, pygame.sprite.Sprite):
    """A quantity of one item, at a place."""

    def __init__(self, item, count, x, y, art):
        pygame.sprite.Sprite.__init__(self)
        self.item = item
        self.count = int(count)
        self.image = art
        self.rect = self.image.get_rect()
        self.pickup_x = x
        self.pickup_y = y
        self.remember_position()

    @property
    def world_x(self):
        return self.pickup_x

    @property
    def world_y(self):
        return self.pickup_y

    @property
    def middle(self):
        return (
            self.pickup_x + self.rect.width / 2,
            self.pickup_y + self.rect.height / 2,
        )

    def within(self, point, reach=REACH):
        return math.dist(self.middle, point) <= reach

    def take(self, backpack):
        """Give up what fits and keep the rest; report what was taken.

        Zero means there was no room, which the player has to be told --
        walking over wood and seeing nothing happen reads as a bug rather than
        as a full pack.
        """
        taken = backpack.add(self.item, self.count)
        self.count -= taken
        if not self.count:
            self.kill()
        return taken

    def update(self, camera_x, camera_y, dt=config.SIM_DT):
        """Nothing happens to a pickup until someone stands on it."""
