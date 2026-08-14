"""What a zombie was carrying.

A table keyed by kind rather than a branch, so a second kind of zombie is a row
here and nothing else anywhere. There is one kind today; the shape is the point.

Rolled once per corpse and returned as whole bundles, because a drop is *one*
pickup holding a count. Three cloth is one thing lying in the grass, not three.
"""

import random
from dataclasses import dataclass

from shooter.systems import world


@dataclass(frozen=True)
class Drop:
    """One line of a table: what, how many, and how often.

    `chance` is per corpse, so a line that never fires still costs nothing to
    declare -- which is what makes the rare things worth walking towards.
    """

    item: object
    least: int
    most: int
    chance: float

    def roll(self, throw):
        """How many of this fall, given a throw of the dice."""
        if throw.random() >= self.chance:
            return 0
        return throw.randint(self.least, self.most)


TABLE = {
    "walker": (
        Drop(world.CLOTH, 1, 2, 0.55),
        Drop(world.METAL, 1, 1, 0.25),
    ),
}


def spoils(kind, throw=random):
    """What one of these leaves behind: pairs of item and count.

    Nothing at all is a perfectly good answer, and the common one -- loot that
    drops every time is not loot, it is a wage.
    """
    return tuple(
        (drop.item, count)
        for drop in TABLE.get(kind, ())
        if (count := drop.roll(throw))
    )
