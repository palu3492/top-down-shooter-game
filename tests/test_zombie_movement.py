"""How a crowd of zombies moves.

Three things a wave used to do wrong: arrive in rank at one speed, converge
until they were a single sprite, and face the same way the whole time however
they were walking.
"""

import math
import random

import pygame
import pytest

from shooter import config
from shooter.entities.zombie import (
    MAX_SHOVE_SPEED,
    PERSONAL_SPACE,
    SHOVE,
    Zombie,
    keep_apart,
    spawn_margin,
)
from shooter.session import Session
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def crowd(display, cash):
    """Six zombies stacked in almost exactly the same place."""
    group = pygame.sprite.Group()
    for index in range(6):
        zombie = Zombie(WINDOW, cash)
        zombie.set_position(2000 + index, 2000 + index)
        zombie.move_position(0, 0)
        group.add(zombie)
    return group


def closest_pair(group):
    listed = list(group)
    return min(
        math.dist(one.get_position(), other.get_position())
        for index, one in enumerate(listed)
        for other in listed[index + 1 :]
    )


# ----------------------------------------------------------------------
# Pace
# ----------------------------------------------------------------------


def test_zombies_do_not_all_walk_at_one_speed(display, cash):
    """A crowd moving at exactly one speed reads as a single object."""
    speeds = {Zombie(WINDOW, cash).zombie_speed for _ in range(20)}
    assert len(speeds) > 1


def test_a_pace_stays_near_the_configured_speed(display, cash):
    for _ in range(30):
        zombie = Zombie(WINDOW, cash)
        assert zombie.zombie_speed == pytest.approx(config.ZOMBIE_SPEED * zombie.pace)
        assert 0.75 < zombie.pace < 1.25


def test_a_stun_wears_off_to_its_own_pace_not_the_crowds(display, cash):
    """The stun timer used to restore the shared constant, which would have
    quietly re-paced every zombie that was ever stunned."""
    zombie = Zombie(WINDOW, cash)
    own = zombie.walking_speed

    zombie.remove_speed(config.STUN_SPEED)
    for _ in range(int(config.STUN_SECONDS * 60) + 5):
        zombie.zombie_speed_timer(1 / 60)

    assert zombie.zombie_speed == own


# ----------------------------------------------------------------------
# Personal space
# ----------------------------------------------------------------------


def test_a_stacked_crowd_pushes_itself_apart(crowd, cash):
    before = closest_pair(crowd)
    assert before < 5, "they start on top of each other"

    for _ in range(240):
        keep_apart(crowd, (0, 0), config.SIM_DT)

    assert closest_pair(crowd) > before * 5


def test_exactly_stacked_zombies_still_separate(display, cash):
    """Nothing to push along, so a fixed direction has to be chosen or they
    sit inside each other for ever."""
    group = pygame.sprite.Group()
    for _ in range(2):
        zombie = Zombie(WINDOW, cash)
        zombie.set_position(1000, 1000)
        group.add(zombie)

    for _ in range(120):
        keep_apart(group, (0, 0), config.SIM_DT)

    assert closest_pair(group) > 1


def test_zombies_far_apart_are_left_alone(display, cash):
    group = pygame.sprite.Group()
    positions = ((0, 0), (900, 900))
    for at in positions:
        zombie = Zombie(WINDOW, cash)
        zombie.set_position(*at)
        group.add(zombie)

    keep_apart(group, (0, 0), config.SIM_DT)

    assert {z.get_position() for z in group} == set(positions)


def test_a_crowd_cannot_shove_a_zombie_faster_than_it_walks(display, cash):
    """Neighbour forces add together in a pack. Left uncapped, the zombie in
    the middle gets fired out of the group and appears to bounce off it."""
    group = pygame.sprite.Group()
    middle = Zombie(WINDOW, cash)
    middle.set_position(1000, 1000)
    group.add(middle)
    for at in ((999, 1000), (1000, 999), (1001, 999), (1001, 1001)):
        zombie = Zombie(WINDOW, cash)
        zombie.set_position(*at)
        group.add(zombie)

    before = middle.get_position()
    keep_apart(group, (0, 0), config.SIM_DT)

    shove_speed = math.dist(before, middle.get_position()) / config.SIM_DT
    assert shove_speed <= middle.zombie_speed * MAX_SHOVE_SPEED + 1e-6


def test_crowding_does_not_knock_a_walking_zombie_backwards(display, cash):
    group = pygame.sprite.Group()
    walker = Zombie(WINDOW, cash)
    walker.set_position(200, WINDOW[1] / 2 - walker.rect.height / 2)
    walker.move_position(0, 0)
    group.add(walker)
    for x in (201, 202, 203):
        neighbour = Zombie(WINDOW, cash)
        neighbour.set_position(x, walker.zombie_y)
        group.add(neighbour)

    before = walker.zombie_x
    walker.move_toward_center(0, 0, config.SIM_DT)
    keep_apart(group, (0, 0), config.SIM_DT)

    assert walker.zombie_x > before


def test_pushing_apart_does_not_depend_on_iteration_order(display, cash):
    """Every push is worked out before anything moves, so a group that happens
    to iterate differently still lands in the same place."""

    def run(reverse):
        # Same seed both times: each zombie draws its own pace when it is
        # built, and comparing two differently paced crowds would say nothing
        # about iteration order.
        random.seed(1234)
        group = pygame.sprite.Group()
        made = []
        for index in range(4):
            zombie = Zombie(WINDOW, cash)
            zombie.set_position(500 + index * 20, 500)
            made.append(zombie)
        for zombie in reversed(made) if reverse else made:
            group.add(zombie)
        keep_apart(group, (0, 0), config.SIM_DT)
        return sorted(round(c, 6) for z in made for c in z.get_position())

    assert run(False) == run(True)


def test_separation_is_frame_rate_independent(display, cash):
    def run(rate):
        group = pygame.sprite.Group()
        for index in range(4):
            zombie = Zombie(WINDOW, cash)
            zombie.set_position(600 + index, 600)
            group.add(zombie)
        for _ in range(rate):
            keep_apart(group, (0, 0), 1 / rate)
        return closest_pair(group)

    assert run(60) == pytest.approx(run(240), rel=0.05)


def test_a_wave_spreads_out_as_it_walks_in(display):
    """The whole point, through a real session: they arrive as a crowd rather
    than as one sprite."""
    game = Session(Viewport(WINDOW))
    idle = dict.fromkeys(range(512), False)

    for zombie in game.zombies:
        zombie.set_position(2600, 2600)
        zombie.move_position(*game.camera)
    assert closest_pair(game.zombies) < 1

    for _ in range(300):
        game.step(idle, config.SIM_DT)

    assert closest_pair(game.zombies) > PERSONAL_SPACE / 3


# ----------------------------------------------------------------------
# Facing
# ----------------------------------------------------------------------


def test_a_zombie_turns_to_face_the_player(display, cash):
    zombie = Zombie(WINDOW, cash)
    zombie.update_anim("MOVE", config.SIM_DT)
    upright = zombie.image

    zombie.rect.center = (60, 60)
    zombie.face_player()

    assert zombie.image is not upright


def test_facing_does_not_change_the_hitbox(display, cash):
    """A rotated sprite needs a bigger surface. Letting the footprint grow with
    it would mean a zombie coming in at forty-five degrees reaching the player
    before one walking straight in -- 144x155 becomes 201x205 on the turn."""
    footprints = set()
    for at in ((80, WINDOW[1] // 2), (80, 80), (WINDOW[0] // 2, 80), (900, 640)):
        zombie = Zombie(WINDOW, cash)
        zombie.update_anim("MOVE", config.SIM_DT)
        zombie.rect.center = at
        zombie.face_player()
        footprints.add(zombie.rect.size)

    assert len(footprints) == 1, footprints


def test_turning_repeatedly_does_not_grow_the_sprite(display, cash):
    """Rotating an already rotated sprite lands it on a bigger surface every
    time. The game loop hid this by re-choosing the frame each step; anything
    that turns without animating would have grown it without bound."""
    zombie = Zombie(WINDOW, cash)
    zombie.update_anim("MOVE", config.SIM_DT)
    zombie.rect.center = (100, 100)

    # Five turns, not fifty: each compounding rotation is about forty per cent
    # bigger than the last, so a high count exhausts memory before it can
    # assert anything. A guard that hangs is worse than one that fails.
    sizes = set()
    for _ in range(5):
        zombie.face_player()
        sizes.add(zombie.image.get_size())

    assert len(sizes) == 1, sizes


def test_the_drawn_sprite_stays_centred_on_the_footprint(display, cash):
    zombie = Zombie(WINDOW, cash)
    zombie.update_anim("MOVE", config.SIM_DT)
    zombie.rect.center = (100, 100)
    zombie.face_player()

    grown_x = zombie.image.get_width() - zombie.rect.width
    grown_y = zombie.image.get_height() - zombie.rect.height
    assert zombie.image_offset == pytest.approx((-grown_x / 2, -grown_y / 2))


def test_up_facing_source_art_points_toward_player(display, cash):
    zombie = Zombie(WINDOW, cash)
    zombie.update_anim("MOVE", 0)
    zombie.rect.center = (100, WINDOW[1] // 2)
    zombie.face_player()

    # Turning from the source's upward heading to the player on the right is
    # a clockwise quarter-turn, swapping width and height.
    assert zombie.image.get_size() == (
        zombie.upright.get_height(),
        zombie.upright.get_width(),
    )


def test_movement_aims_the_hitbox_center_at_the_player(display, cash):
    zombie = Zombie(WINDOW, cash)
    zombie.set_position(0, WINDOW[1] / 2 - zombie.rect.height / 2)
    zombie.move_position(0, 0)
    before = zombie.get_position()

    zombie.move_toward_center(0, 0, config.SIM_DT)

    assert zombie.zombie_x > before[0]
    assert zombie.zombie_y == pytest.approx(before[1])


def test_a_zombie_on_the_player_does_not_spin(display, cash):
    """No direction to face, and atan2(0, 0) would point it east."""
    zombie = Zombie(WINDOW, cash)
    zombie.update_anim("MOVE", config.SIM_DT)
    zombie.rect.center = (WINDOW[0] // 2, WINDOW[1] // 2)
    upright = zombie.image

    zombie.face_player()

    assert zombie.image is upright


# ----------------------------------------------------------------------
# Pace must not undo the promises the rest of the game makes
# ----------------------------------------------------------------------


@pytest.mark.parametrize("pace", [0.82, 0.9, 1.0, 1.1, 1.18])
def test_every_zombie_gets_the_same_warning_whatever_its_pace(display, pace):
    """AT15 made the spawn ring a number of *seconds*, not a number of pixels.
    Reading the shared speed instead of the zombie's own gave the quickest of
    them a fifth less warning than the setting claims -- and the test that was
    supposed to guard it divided the margin by the same shared constant, so it
    could not tell."""
    walking_speed = config.ZOMBIE_SPEED * pace
    seconds = spawn_margin(walking_speed) / walking_speed
    assert seconds == pytest.approx(config.SPAWN_LEAD_SECONDS)


def test_a_fast_zombie_really_does_start_further_out(display, cash):
    quick = spawn_margin(config.ZOMBIE_SPEED * 1.18)
    slow = spawn_margin(config.ZOMBIE_SPEED * 0.82)
    assert quick > slow


def test_the_sprite_clearance_still_wins_at_a_crawl(display):
    """The floor is what stops a zombie appearing already half on screen, and
    a slow pace must not sneak under it."""
    assert spawn_margin(1.0) >= max(config.ZOMBIE_SIZE)


def test_a_stunned_zombie_is_shoved_at_its_stunned_pace(display, cash):
    """A stun exists to slow a zombie down. Pushing it out of a pile at the
    crowd's speed flung it further than it can ever walk, undoing the stun at
    the moment it should read most clearly."""
    group = pygame.sprite.Group()
    for _ in range(2):
        zombie = Zombie(WINDOW, cash)
        zombie.set_position(1000, 1000)
        group.add(zombie)

    stunned = next(iter(group))
    stunned.remove_speed(config.STUN_SPEED)
    before = stunned.get_position()

    keep_apart(group, (0, 0), config.SIM_DT)

    shoved = math.dist(stunned.get_position(), before) / config.SIM_DT
    assert shoved <= stunned.zombie_speed * SHOVE + 1
    assert shoved < config.ZOMBIE_SPEED, "shoved faster than it can walk"


def test_a_brisk_zombie_steps_aside_faster_than_a_slow_one(display, cash):
    def shove_rate(pace):
        group = pygame.sprite.Group()
        pair = []
        for _ in range(2):
            zombie = Zombie(WINDOW, cash)
            zombie.pace = pace
            zombie.zombie_speed = zombie.walking_speed
            zombie.set_position(1000, 1000)
            group.add(zombie)
            pair.append(zombie)
        before = pair[0].get_position()
        keep_apart(group, (0, 0), config.SIM_DT)
        return math.dist(pair[0].get_position(), before)

    assert shove_rate(1.18) > shove_rate(0.82)
