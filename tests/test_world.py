"""The layer of things that stay where they are.

`Session` had groups for zombies, bullets, grenades and power-ups -- everything
that moves and nothing that stays. This is the half the resource arc needs: a
tree is not one more sprite, it is a kind of thing the game did not have.
"""

import pygame
import pytest

from shooter import config, weapons
from shooter.assets import load_scaled
from shooter.entities.props import Harvestable, Prop
from shooter.session import PLAYER_SOLID, Session
from shooter.systems import world
from shooter.systems.levels import LEVELS, LevelRules, rules_for
from shooter.viewport import Viewport

WINDOW = (1080, 720)
IDLE = dict.fromkeys(range(512), False)


@pytest.fixture
def game(display):
    made = Session(Viewport(WINDOW))
    made.zombies.empty()
    return made


@pytest.fixture
def tree(display):
    """In a group, because `Sprite.alive()` is about group membership -- a
    loose sprite reports dead from the moment it is built, which made
    `assert not tree.alive()` pass without anything being felled."""
    made = world.make(world.Standing(world.TREE, (1000, 1000)))
    pygame.sprite.Group(made)
    return made


ALONE = (world.Standing(world.TREE, (2000, 2000)),)


class OneTree:
    """A world with a single tree, so the collision tests are not hostage to
    wherever the authored map happens to put its next prop."""

    layout = ALONE

    def __init__(self, *args, **kwargs):
        pass

    def advance(self, *args, **kwargs):
        pass

    def draw(self, *args, **kwargs):
        pass


@pytest.fixture
def clearing(display):
    made = Session(Viewport(WINDOW), rules=OneTree)
    made.zombies.empty()
    return made


def knife():
    return weapons.equip(weapons.KNIFE)


def beside(session, prop, offset):
    """Put the player at a world offset from a prop, without walking there."""
    session.camera_x = session.window[0] / 2 - (prop.middle[0] + offset[0])
    session.camera_y = session.window[1] / 2 - (prop.middle[1] + offset[1])
    session.previous_camera = session.camera
    return session


def walk(session, key, steps=60):
    pressed = dict(IDLE)
    pressed[key] = True
    for _ in range(steps):
        session.step(pressed, config.SIM_DT)


# ----------------------------------------------------------------------
# What is in a thing
# ----------------------------------------------------------------------


def test_a_blow_reports_what_it_took_out(tree):
    assert tree.hit(30, knife()) == 30
    assert tree.health == world.TREE_HEALTH - 30


def test_the_last_blow_only_counts_what_was_left(tree):
    """Overkill must not pay out. A tree with two health in it is worth two,
    however hard the last swing was -- otherwise AT43's yield rounds up on
    every felling."""
    tree.health = 2

    assert tree.hit(50, knife()) == 2
    assert tree.health == 0


def test_a_thing_used_up_stops_being_in_the_world(tree):
    tree.hit(world.TREE_HEALTH, knife())

    assert tree.health == 0
    assert not tree.alive()


def test_what_is_left_is_what_the_health_says(tree):
    assert tree.left == 1

    tree.hit(world.TREE_HEALTH / 4, knife())

    assert tree.left == pytest.approx(0.75)


def test_nothing_lands_with_the_wrong_tool(display):
    fussy = Harvestable(pygame.Surface((120, 140)), 0, 0, 100, tool=weapons.M16.id)

    assert fussy.hit(50, knife()) == 0
    assert fussy.health == 100
    assert fussy.hit(50, weapons.equip(weapons.M16)) == 50


def test_a_thing_with_no_tool_named_takes_anything(tree):
    assert tree.tool is None
    assert tree.hit(10, weapons.equip(weapons.M16)) == 10


@pytest.mark.parametrize("damage", [0, -5])
def test_a_blow_that_is_not_one_does_nothing(tree, damage):
    assert tree.hit(damage, knife()) == 0
    assert tree.health == world.TREE_HEALTH


# ----------------------------------------------------------------------
# Footprints
# ----------------------------------------------------------------------


def test_what_blocks_excludes_transparent_padding(tree):
    assert tree.footprint.width < tree.rect.width
    assert tree.footprint.height < tree.rect.height


def test_a_footprint_tracks_the_opaque_part_of_the_art(tree):
    assert tree.footprint == pygame.Rect(1009, 1001, 120, 147)


@pytest.mark.parametrize(
    ("kind", "asset", "scale", "size", "solid"),
    (
        (world.TREE, world.TREE_SPRITE, world.TREE_SCALE, (138, 161), world.TREE_SOLID),
        (world.ROCK, world.ROCK_SPRITE, world.ROCK_SCALE, (130, 104), world.ROCK_SOLID),
    ),
)
def test_harvestable_art_comes_from_the_cached_asset_pipeline(
    display, kind, asset, scale, size, solid
):
    standing = world.make(world.Standing(kind, (0, 0)))

    assert standing.image is load_scaled(asset, scale, True)
    assert standing.image.get_size() == size
    assert standing.footprint == pygame.Rect(solid)


@pytest.mark.parametrize(
    ("kind", "damage_art", "scale", "exact_footprint"),
    (
        (world.TREE, world.TREE_DAMAGE_SPRITES, world.TREE_SCALE, False),
        (world.ROCK, world.ROCK_DAMAGE_SPRITES, world.ROCK_SCALE, True),
    ),
)
def test_mining_swaps_in_progressively_destroyed_art(
    display, kind, damage_art, scale, exact_footprint
):
    standing = world.make(world.Standing(kind, (0, 0)))
    blow = standing.full / (len(damage_art) + 1)
    size = standing.image.get_size()
    footprint = standing.image.get_bounding_rect(min_alpha=1)
    anchor = footprint.midbottom

    for expected in standing.damage_art:
        standing.hit(blow, knife())
        assert standing.image is expected
        assert standing.image.get_size() == size
        damaged_anchor = standing.image.get_bounding_rect(min_alpha=1).midbottom
        assert damaged_anchor[1] == anchor[1]
        assert abs(damaged_anchor[0] - anchor[0]) <= 1
        if exact_footprint:
            assert standing.image.get_bounding_rect(min_alpha=1) == footprint


def test_most_things_are_not_solid_at_all(display):
    assert Prop(pygame.Surface((100, 80)), 0, 0).footprint is None


# ----------------------------------------------------------------------
# Walking into them
# ----------------------------------------------------------------------


# Which way each key sends the player, and so which side to approach from.
# `W` raises the camera, which lowers the player's world y -- so walking into a
# tree with `W` means starting below it.
APPROACHES = (
    (pygame.K_w, (0, 260)),
    (pygame.K_s, (0, -260)),
    (pygame.K_a, (260, 0)),
    (pygame.K_d, (-260, 0)),
)


@pytest.mark.parametrize(("key", "offset"), APPROACHES)
def test_a_tree_cannot_be_walked_through_from_any_side(clearing, key, offset):
    """Both axes, because they are guarded separately -- dropping either guard
    leaves a tree solid from two directions and open from the other two."""
    tree = next(iter(clearing.props))
    beside(clearing, tree, offset)
    before = clearing.camera

    walk(clearing, key)

    moved = max(
        abs(clearing.camera[0] - before[0]), abs(clearing.camera[1] - before[1])
    )
    assert 0 < moved < 260, f"walked {moved} of the 260 to the tree"


def test_walking_past_one_is_not_walking_into_it(clearing):
    tree = next(iter(clearing.props))
    beside(clearing, tree, (600, 0))
    before = clearing.camera_y

    walk(clearing, pygame.K_w)

    assert clearing.camera_y - before == pytest.approx(config.PLAYER_SPEED, abs=1)


def test_a_corner_slides_rather_than_sticking(clearing):
    """One axis at a time, so walking into a tree at an angle carries on along
    it instead of stopping dead."""
    tree = next(iter(clearing.props))
    beside(clearing, tree, (0, 260))
    before = clearing.camera

    pressed = dict(IDLE)
    pressed[pygame.K_w] = True
    pressed[pygame.K_a] = True
    for _ in range(60):
        clearing.step(pressed, config.SIM_DT)

    assert clearing.camera[0] != before[0], "stopped dead instead of sliding"


def test_something_already_inside_one_can_walk_out(clearing):
    """A player who ends up in a footprint must not be held there."""
    tree = next(iter(clearing.props))
    beside(clearing, tree, (0, 0))
    assert clearing._blocked(clearing.camera_x, clearing.camera_y)
    before = clearing.camera_x

    walk(clearing, pygame.K_a, steps=5)

    assert clearing.camera_x != before


def test_the_edge_of_the_map_still_holds(clearing):
    clearing.props.empty()
    walk(clearing, pygame.K_d, steps=2000)

    assert clearing.camera_x >= -(config.WORLD[0] - WINDOW[0])


def test_the_footprint_does_not_follow_the_aim(game):
    """Read from a constant rather than `human.rect`, which grows and shrinks
    as the player turns -- a hitbox that depends on where you are aiming is not
    a hitbox."""
    game.aim_at((0, 0))
    game.step(IDLE, config.SIM_DT)
    facing_one_way = game._standing_at(0, 0).size

    game.aim_at((WINDOW[0], WINDOW[1]))
    game.step(IDLE, config.SIM_DT)

    assert game._standing_at(0, 0).size == facing_one_way == PLAYER_SOLID


# ----------------------------------------------------------------------
# Placement
# ----------------------------------------------------------------------


def test_what_stands_in_a_game_comes_from_its_rules(game):
    placed = [(one.kind, one.at) for one in world.STARTER]
    standing = [(prop.prop_x, prop.prop_y) for prop in game.props]

    assert len(standing) == len(placed)
    assert set(standing) == {one.at for one in world.STARTER}


def test_a_mode_that_declares_nothing_has_an_empty_world(display):
    class Bare(OneTree):
        layout = ()

    assert len(Session(Viewport(WINDOW), rules=Bare).props) == 0


def test_a_level_says_what_stands_in_it(display):
    mine = (world.Standing(world.ROCK, (400, 400)),)
    level = LEVELS[0].__class__(number=9, waves=1, opening=1, growth=1, props=mine)

    made = Session(Viewport(WINDOW), rules=rules_for(level))

    assert len(made.props) == 1
    assert next(iter(made.props)).label == "MINE"


def test_every_authored_level_has_a_world(display):
    for level in LEVELS:
        assert level.props, level.number
        assert LevelRules(WINDOW, pygame.sprite.Group(), None, level=level).layout


def test_a_placement_naming_nothing_is_an_error():
    with pytest.raises(world.UnknownStandingError):
        world.make(world.Standing("volcano", (0, 0)))


def test_a_layout_is_data_until_it_is_built():
    """Nothing in a level definition touches a `Surface`, so a level can be
    read and compared without a display."""
    for standing in world.STARTER:
        assert isinstance(standing.at, tuple)
        assert isinstance(standing.kind, str)


# ----------------------------------------------------------------------
# Using them
# ----------------------------------------------------------------------


def test_e_on_a_tree_chops_it_rather_than_opening_a_shop(game):
    tree = next(prop for prop in game.props if prop.label == "CHOP")
    beside(game, tree, (0, 120))
    assert game.nearby is tree

    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))

    assert game.shopping is False
    assert tree.health == world.TREE_HEALTH - game.equipped.damage


def test_e_on_the_stand_still_opens_the_shop(game):
    stand = next(prop for prop in game.props if prop.label == "GUN STAND")
    beside(game, stand, (0, 120))

    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))

    assert game.shopping is True


def test_chopping_a_tree_down_takes_it_out_of_the_world(game):
    tree = next(prop for prop in game.props if prop.label == "CHOP")
    beside(game, tree, (0, 120))
    standing = len(game.props)

    for _ in range(20):
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        if not tree.alive():
            break

    assert not tree.alive()
    assert len(game.props) == standing - 1


def test_a_felled_tree_stops_blocking_the_way(game):
    tree = next(prop for prop in game.props if prop.label == "CHOP")
    beside(game, tree, (0, 120))
    for _swing in range(50):
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        if not tree.alive():
            break
    else:
        pytest.fail("the tree never came down")

    assert not game._blocked(*game.camera)
