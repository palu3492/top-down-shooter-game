"""What is standing in a level, and where.

Authored rather than scattered. A random field of trees is the same field every
time it is looked at and no field in particular -- placing them by hand is what
lets a level have a clearing worth crossing to, or a wood to be cornered in.

A layout is data. Nothing here builds a `Surface` until `build` is called, so a
level can be read, compared and tested without a display.
"""

from dataclasses import dataclass

from shooter.entities import shapes
from shooter.entities.props import Harvestable, Prop

STAND = "stand"
TREE = "tree"
ROCK = "rock"

STAND_SPRITE = "Wall Items/gun_on_wall.png"

# Trees are worth about twice a rock and take longer. The numbers are health,
# which AT43 turns into how much wood or metal comes out.
TREE_HEALTH = 120
ROCK_HEALTH = 200

# Solid boxes, deliberately smaller than the pictures. A canopy is drawn far
# wider than the part of a tree you would bump into, and a wood whose footprints
# match its sprites is a maze.
TREE_SOLID = (34, 34)
ROCK_SOLID = (78, 44)
STAND_SOLID = (110, 110)


@dataclass(frozen=True)
class Standing:
    """One thing, and where it stands. Level definitions are made of these."""

    kind: str
    at: tuple


def make(standing):
    """Turn a placement into the thing itself."""
    x, y = standing.at
    if standing.kind == STAND:
        return Prop(STAND_SPRITE, x, y, label="GUN STAND", solid=STAND_SOLID)
    if standing.kind == TREE:
        return Harvestable(
            shapes.tree(), x, y, TREE_HEALTH, label="CHOP", solid=TREE_SOLID
        )
    if standing.kind == ROCK:
        return Harvestable(
            shapes.rock(), x, y, ROCK_HEALTH, label="MINE", solid=ROCK_SOLID
        )
    raise UnknownStandingError(standing.kind)


class UnknownStandingError(KeyError):
    """A placement naming something nothing knows how to build."""


def build(layout):
    return [make(standing) for standing in layout]


# The opening corner. The player starts near (540, 360) and the stand is a walk
# down and to the right of that -- close enough to reach on the first wave with
# nothing but a knife, far enough to be a decision.
STARTER = (
    Standing(STAND, (1350, 620)),
    Standing(TREE, (760, 980)),
    Standing(TREE, (900, 1120)),
    Standing(TREE, (620, 1180)),
    Standing(ROCK, (1180, 1010)),
    Standing(TREE, (1620, 300)),
    Standing(TREE, (1780, 430)),
    Standing(ROCK, (1560, 560)),
    Standing(TREE, (350, 640)),
    Standing(ROCK, (240, 940)),
    Standing(TREE, (2050, 880)),
    Standing(TREE, (2190, 1020)),
)
