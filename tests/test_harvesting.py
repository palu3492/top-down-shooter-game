"""Chopping a tree into wood, and wood into the backpack.

The backpack was built in AT37 and nothing had used it since. This is what it
was for -- and the rule that matters most is the one about what happens when it
will not all fit.
"""

import pygame
import pytest

from shooter import config, items, weapons
from shooter.entities.pickups import Pickup
from shooter.entities.props import Yield
from shooter.session import Session
from shooter.systems import world
from shooter.viewport import Viewport

WINDOW = (1080, 720)
IDLE = dict.fromkeys(range(512), False)
AWAY = (2400, 2400)


class Bare:
    """A game with nothing standing in it, so a test places its own."""

    layout = ()

    def __init__(self, *args, **kwargs):
        pass

    def advance(self, *args, **kwargs):
        pass

    def draw(self, *args, **kwargs):
        pass


@pytest.fixture
def game(display):
    made = Session(Viewport(WINDOW), rules=Bare)
    made.zombies.empty()
    return made


@pytest.fixture
def tree(display):
    made = world.make(world.Standing(world.TREE, (1000, 1000)))
    pygame.sprite.Group(made)
    return made


class Tool:
    """Something to swing, without needing a whole weapon."""

    def __init__(self, damage, weapon_id="knife"):
        self.damage = damage
        self.weapon = type("Named", (), {"id": weapon_id})()


def stand_on(session, at):
    session.camera_x = session.window[0] / 2 - at[0]
    session.camera_y = session.window[1] / 2 - at[1]
    session.previous_camera = session.camera
    return session


def step(session, seconds=config.SIM_DT):
    for _ in range(max(1, int(seconds * config.SIM_HZ))):
        session.step(IDLE, config.SIM_DT)


def fell(thing, tool):
    won = 0
    for _ in range(1000):
        if not thing.alive():
            return won
        won += thing.harvest(tool.damage, tool)
    raise AssertionError("it never came down")


# ----------------------------------------------------------------------
# What a thing is worth
# ----------------------------------------------------------------------


@pytest.mark.parametrize("damage", [1, 3, 7, 20, 50, 119, 120, 500])
def test_a_whole_tree_is_worth_the_same_however_it_is_cut(tree, damage):
    """The promise of the whole ticket. A rate per swing would mean a sharper
    axe fells it in fewer swings and comes away with less wood; a total means a
    better tool is only faster."""
    assert fell(tree, Tool(damage)) == world.TREE_WOOD


def test_a_rock_is_worth_its_metal(display):
    rock = world.make(world.Standing(world.ROCK, (0, 0)))
    pygame.sprite.Group(rock)

    assert fell(rock, Tool(37)) == world.ROCK_METAL


def test_yield_keeps_pace_with_what_has_been_taken_out(tree):
    """Half a tree is half its wood, so the health bar reads as how much is
    still in it rather than only as how close it is to falling."""
    tool = Tool(world.TREE_HEALTH // 2)

    assert tree.harvest(tool.damage, tool) == world.TREE_WOOD // 2
    assert tree.left == pytest.approx(0.5)


def test_nothing_comes_out_of_a_thing_that_yields_nothing(display):
    from shooter.entities import shapes
    from shooter.entities.props import Harvestable

    bare = Harvestable(shapes.rock(), 0, 0, 50)
    pygame.sprite.Group(bare)

    assert bare.harvest(50, Tool(50)) == 0


def test_the_wrong_tool_shakes_nothing_loose(display):
    from shooter.entities import shapes
    from shooter.entities.props import Harvestable

    fussy = Harvestable(
        shapes.tree(), 0, 0, 100, tool=weapons.M16.id, yields=Yield(world.WOOD, 5)
    )
    pygame.sprite.Group(fussy)

    assert fussy.harvest(50, Tool(50, "knife")) == 0
    assert fussy.health == 100


def test_a_fraction_of_an_item_is_not_dropped_and_not_lost(tree):
    """One damage at a time is the worst case for a rate: it rounds to nothing
    on every single blow, and the tree must still pay out in full."""
    tool = Tool(1)
    early = [tree.harvest(1, tool) for _ in range(11)]

    assert early.count(0) > 0, "not every blow yields"
    assert sum(early) < world.TREE_WOOD
    assert sum(early) + fell(tree, tool) == world.TREE_WOOD


# ----------------------------------------------------------------------
# What is on the ground
# ----------------------------------------------------------------------


def test_chopping_leaves_a_pile_where_the_tree_was(game):
    tree = world.make(world.Standing(world.TREE, AWAY))
    game.props.add(tree)
    stand_on(game, (AWAY[0], AWAY[1] + 130))

    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))

    assert len(game.dropped) == 1
    pile = next(iter(game.dropped))
    assert pile.item is world.WOOD
    assert pile.count > 0


def test_chopping_again_tops_up_the_pile_rather_than_starting_another(game):
    """Ten wood is one thing to look at and one thing to draw, never ten."""
    tree = world.make(world.Standing(world.TREE, AWAY))
    game.props.add(tree)
    stand_on(game, (AWAY[0], AWAY[1] + 130))

    for _ in range(3):
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))

    assert len(game.dropped) == 1
    assert next(iter(game.dropped)).count == world.TREE_WOOD


def test_wood_and_metal_do_not_share_a_pile(game):
    game._spill(world.WOOD, 3, AWAY)
    game._spill(world.METAL, 3, AWAY)

    assert len(game.dropped) == 2


def test_a_pile_far_from_another_is_its_own(game):
    game._spill(world.WOOD, 3, AWAY)
    game._spill(world.WOOD, 3, (AWAY[0] + 900, AWAY[1]))

    assert len(game.dropped) == 2


# ----------------------------------------------------------------------
# Into the backpack
# ----------------------------------------------------------------------


def test_walking_over_a_pile_puts_it_in_the_backpack(game):
    game.dropped.add(world.spilled(world.WOOD, 6, AWAY))
    stand_on(game, AWAY)

    step(game)

    assert game.backpack.count(world.WOOD) == 6
    assert len(game.dropped) == 0
    assert game.notice == "+6 WOOD"


def test_a_pile_out_of_reach_is_left_alone(game):
    game.dropped.add(world.spilled(world.WOOD, 6, AWAY))
    stand_on(game, (AWAY[0] + 400, AWAY[1]))

    step(game)

    assert game.backpack.count(world.WOOD) == 0
    assert len(game.dropped) == 1


def test_what_will_not_fit_stays_on_the_ground(game):
    """The rule the whole design turns on. Room for five of twelve takes five
    and leaves seven -- the pile shrinks by exactly what was taken."""
    game.backpack = items.Backpack(slots=1)
    game.backpack.add(world.WOOD, world.WOOD.stack - 5)
    game.dropped.add(world.spilled(world.WOOD, 12, AWAY))
    stand_on(game, AWAY)

    step(game)

    assert game.backpack.count(world.WOOD) == world.WOOD.stack
    assert next(iter(game.dropped)).count == 7
    assert game.notice == "+5 WOOD"


def test_a_full_backpack_says_so_rather_than_doing_nothing(game):
    """Walking over wood and seeing nothing happen reads as a bug."""
    game.backpack = items.Backpack(slots=1)
    game.backpack.add(world.METAL, world.METAL.stack)
    game.dropped.add(world.spilled(world.WOOD, 4, AWAY))
    stand_on(game, AWAY)

    step(game)

    assert game.notice == "NO ROOM"
    assert next(iter(game.dropped)).count == 4
    assert game.backpack.count(world.WOOD) == 0


def test_a_notice_does_not_stay_up_for_ever(game):
    game.dropped.add(world.spilled(world.WOOD, 2, AWAY))
    stand_on(game, AWAY)
    step(game)
    assert game.notice

    step(game, seconds=5)

    assert game.notice is None


def test_a_pile_gives_up_only_what_it_has(display):
    pack = items.Backpack()
    pile = Pickup(world.WOOD, 3, 0, 0, world.LOOKS[world.WOOD.id]())

    assert pile.take(pack) == 3
    assert pack.count(world.WOOD) == 3
    assert not pile.alive()


def test_a_chopped_tree_ends_up_carried(game):
    """The whole loop, end to end: swing, drop, walk over, carry."""
    tree = world.make(world.Standing(world.TREE, AWAY))
    game.props.add(tree)
    stand_on(game, (AWAY[0], AWAY[1] + 130))

    for _ in range(20):
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        if not tree.alive():
            break
    stand_on(game, next(iter(game.dropped)).middle)
    step(game)

    assert game.backpack.count(world.WOOD) == world.TREE_WOOD
    assert len(game.dropped) == 0
