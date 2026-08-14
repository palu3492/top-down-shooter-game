"""What is standing in a level, and where.

Authored rather than scattered. A random field of trees is the same field every
time it is looked at and no field in particular -- placing them by hand is what
lets a level have a clearing worth crossing to, or a wood to be cornered in.

A layout is data. Nothing here builds a `Surface` until `build` is called, so a
level can be read, compared and tested without a display.
"""

from dataclasses import dataclass

from shooter import items
from shooter.entities import shapes
from shooter.entities.pickups import Pickup
from shooter.entities.props import Harvestable, Prop, Yield

STAND = "stand"
TREE = "tree"
ROCK = "rock"

STAND_SPRITE = "Wall Items/gun_on_wall.png"

WOOD = items.register(items.Item("wood", "Wood", items.RESOURCE, stack=25))
METAL = items.register(items.Item("metal", "Metal", items.RESOURCE, stack=25))

# What a pickup of each looks like on the ground. An `Item` carries an icon for
# the pack; a `Pickup` carries its own picture, because a log lying in grass and
# a wood icon in a slot are different pictures of the same thing.
LOOKS = {WOOD.id: shapes.wood, METAL.id: shapes.metal}

# Health is how much is left in a thing; these are what a whole one is worth.
# Declared as a total and stored as a rate, so what a tree pays out is a
# property of the tree rather than of how many swings it took to fell.
TREE_HEALTH = 120
ROCK_HEALTH = 200
TREE_WOOD = 10
ROCK_METAL = 8

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
            shapes.tree(),
            x,
            y,
            TREE_HEALTH,
            yields=Yield(WOOD, TREE_WOOD),
            label="CHOP",
            solid=TREE_SOLID,
        )
    if standing.kind == ROCK:
        return Harvestable(
            shapes.rock(),
            x,
            y,
            ROCK_HEALTH,
            yields=Yield(METAL, ROCK_METAL),
            label="MINE",
            solid=ROCK_SOLID,
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


def spilled(item, count, at):
    """A pickup of this, lying here.

    Centred on the point rather than hung off it by a corner, so a pile drops
    where the tree stood instead of down and to the right of it.
    """
    art = LOOKS[item.id]()
    return Pickup(
        item,
        count,
        at[0] - art.get_width() / 2,
        at[1] - art.get_height() / 2,
        art,
    )
