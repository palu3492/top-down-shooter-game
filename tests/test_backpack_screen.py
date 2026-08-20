"""Looking at what you are carrying.

Four merges of picking things up with no way to see any of them. This is the
screen, and the two things it can do to what it shows.
"""

import pygame
import pytest

from shooter import config, game, items, weapons
from shooter.gameplay import BACKPACK, GameplayScene
from shooter.scenes import SceneStack
from shooter.settings import Settings
from shooter.systems import world
from shooter.ui import menu, packfront
from shooter.viewport import Viewport

WINDOW = (1080, 720)
SIZES = ((1080, 720), (1280, 720), (1600, 900), (1920, 1080), (2560, 1440))


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    yield made
    made.clear()


@pytest.fixture
def playing(stack):
    scene = GameplayScene(stack.window, stack.manager)
    stack.push(scene)
    scene.session.zombies.empty()
    return scene


@pytest.fixture
def pack(stack, playing):
    playing.session.backpack.add(world.WOOD, 8)
    playing.session.backpack.add(world.METAL, 3)
    route(stack, press(stack, pygame.K_TAB))
    return stack.top


def press(stack, key):
    return stack.top.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def route(stack, action):
    return game.route(action, stack, stack.window, Settings())


def click(scene, at):
    scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=at))


# ----------------------------------------------------------------------
# Opening it
# ----------------------------------------------------------------------


def test_tab_asks_for_the_backpack(playing):
    assert press_on(playing, pygame.K_TAB) == BACKPACK


def press_on(scene, key):
    return scene.handle(pygame.event.Event(pygame.KEYDOWN, key=key))


def test_tab_opens_it(stack, playing):
    route(stack, press(stack, pygame.K_TAB))

    assert isinstance(stack.top, packfront.BackpackScreen)
    assert stack.top.session is playing.session


def test_tab_closes_it_again(stack, pack):
    route(stack, press(stack, pygame.K_TAB))

    assert isinstance(stack.top, GameplayScene)


def test_escape_closes_it_too(stack, pack):
    route(stack, press(stack, pygame.K_ESCAPE))

    assert isinstance(stack.top, GameplayScene)
    assert press(stack, pygame.K_ESCAPE) is not None, "escape still pauses the game"


def test_it_stops_the_world(stack, pack):
    """A scene rather than an overlay, which is the whole of what pausing is.
    The gun stand deliberately does not; a pack is not something the wave
    should punish you for opening."""
    assert stack.simulates is False


def test_the_game_is_still_there_behind_it(stack, playing, pack):
    assert pack.opaque is False
    assert playing in stack.visible()


@pytest.mark.parametrize("window", SIZES)
def test_it_lays_out_at_every_window_the_game_supports(display, window):
    made = SceneStack(Viewport(window))
    play = GameplayScene(made.window, made.manager)
    made.push(play)
    try:
        made.push(packfront.BackpackScreen(made.window, made.manager, play.session))
        assert len(made.top.slots) == play.session.backpack.slots
    finally:
        made.clear()


# ----------------------------------------------------------------------
# What it shows
# ----------------------------------------------------------------------


def test_there_is_a_box_for_every_slot_and_every_weapon(stack, playing, pack):
    assert len(pack.slots) == playing.session.backpack.slots
    assert len(pack.hands) == len(playing.session.carried)


def test_boxes_do_not_sit_on_top_of_each_other(pack):
    boxes = [*pack.slots, *pack.hands]
    for index, box in enumerate(boxes):
        for other in boxes[index + 1 :]:
            assert not box.colliderect(other), (box, other)


def test_a_resource_is_drawn_with_what_it_looks_like(display):
    assert packfront.icon(world.WOOD) is not None
    assert packfront.icon(world.METAL) is not None


def test_a_gun_with_art_is_drawn_with_it(display):
    assert packfront.icon(weapons.M16) is not None
    assert packfront.icon(weapons.SHOTGUN) is not None


def test_something_with_no_art_says_its_name_instead(display):
    """The SMG and the sniper have no icon, and neither does ammunition."""
    assert packfront.icon(weapons.SMG) is None
    assert packfront.icon(weapons.RIFLE_ROUNDS) is None


def test_drawing_it_touches_nothing(stack, playing, pack):
    before = [(one.item, one.count) for one in playing.session.backpack]
    surface = pygame.Surface(WINDOW)

    stack.draw(surface, 1.0)

    assert [(one.item, one.count) for one in playing.session.backpack] == before


# ----------------------------------------------------------------------
# Dropping
# ----------------------------------------------------------------------


def test_clicking_a_slot_puts_it_on_the_ground(playing, pack):
    session = playing.session
    held = next(iter(session.backpack))
    # Read now: `remove` empties the very `Stack` this is holding.
    item, count = held.item, held.count

    click(pack, pack.slots[0].center)

    assert session.backpack.count(item) == 0
    assert len(session.dropped) == 1
    assert next(iter(session.dropped)).count == count


def test_what_is_dropped_lands_at_your_feet(playing, pack):
    session = playing.session

    click(pack, pack.slots[0].center)

    pile = next(iter(session.dropped))
    assert pile.middle == pytest.approx(session._muzzle(), abs=1)


def test_clicking_an_empty_slot_does_nothing(playing, pack):
    session = playing.session
    before = len(session.backpack)

    click(pack, pack.slots[-1].center)

    assert len(session.backpack) == before
    assert len(session.dropped) == 0


def test_clicking_nowhere_in_particular_does_nothing(playing, pack):
    click(pack, (5, 5))

    assert len(playing.session.dropped) == 0


def test_dropping_what_you_do_not_have_does_nothing(playing):
    session = playing.session

    assert session.drop(world.CLOTH, 5) == 0
    assert len(session.dropped) == 0


def test_a_drop_can_be_picked_straight_back_up(playing, pack):
    session = playing.session
    was = session.backpack.count(world.WOOD)

    click(pack, pack.slots[0].center)
    session.step(dict.fromkeys(range(512), False), config.SIM_DT)

    assert session.backpack.count(world.WOOD) == was


# ----------------------------------------------------------------------
# Equipping
# ----------------------------------------------------------------------


def test_the_number_keys_still_equip_from_in_here(playing, pack):
    session = playing.session
    session.carried.append(weapons.equip(weapons.M16))

    press_on(pack, pygame.K_2)

    assert session.equipped.weapon.id == weapons.M16.id


def test_clicking_a_weapon_equips_it(playing, pack):
    session = playing.session
    session.carried.append(weapons.equip(weapons.M16))
    pack.open()

    click(pack, pack.hands[1].center)

    assert session.equipped.weapon.id == weapons.M16.id


def test_the_one_in_hand_is_the_one_marked(playing, pack):
    session = playing.session
    session.carried.append(weapons.equip(weapons.M16))
    session.equip_slot(1)

    assert session.equipped is session.carried[1]


def test_closing_and_reopening_shows_what_changed(stack, playing, pack):
    """The slots are laid out when the screen opens, so a pack that grew while
    it was shut has somewhere to be drawn."""
    playing.session.carried.append(weapons.equip(weapons.M16))
    route(stack, press(stack, pygame.K_TAB))

    route(stack, press(stack, pygame.K_TAB))

    assert len(stack.top.hands) == len(playing.session.carried)


def test_the_shell_knows_where_tab_goes(stack, playing):
    """`route` is the one place navigation is decided, and it reaches for the
    session of the scene that asked."""
    assert route(stack, BACKPACK) is not False, "only quitting says False"
    assert isinstance(stack.top, packfront.BackpackScreen)

    route(stack, menu.BACK)

    assert isinstance(stack.top, GameplayScene)


def test_the_pointer_comes_back_for_a_screen_you_click(stack, playing):
    """Gameplay hides the system pointer and draws a crosshair. A screen worked
    with the mouse needs the real one, and gets it by not simulating -- which
    an overlay like the gun stand would have had to arrange by hand."""
    assert pygame.mouse.get_visible() is False, "the crosshair is up in a game"

    route(stack, press(stack, pygame.K_TAB))

    assert pygame.mouse.get_visible() is True


@pytest.mark.parametrize("slots", [1, 12, 24, items.MOST_SLOTS])
@pytest.mark.parametrize("window", SIZES)
def test_it_opens_however_big_the_pack_is(display, window, slots):
    """A pack can be made bigger -- that is what a better backpack would be --
    and a fixed slot size meant forty of them did not fit. `open` raised, the
    shell swallowed it, and `Tab` visibly did nothing."""
    made = SceneStack(Viewport(window))
    play = GameplayScene(made.window, made.manager)
    made.push(play)
    play.session.carried = weapons.everything()[: weapons.MAX_SLOTS]
    play.session.backpack.resize(slots)
    try:
        screen = packfront.BackpackScreen(made.window, made.manager, play.session)
        made.push(screen)

        assert len(screen.slots) == slots
        assert len(screen.hands) == len(play.session.carried)
        held = pygame.Rect((0, 0), tuple(window))
        for box in (*screen.slots, *screen.hands):
            assert held.contains(box), (box, window)
    finally:
        made.clear()


@pytest.mark.parametrize("slots", [12, items.MOST_SLOTS])
def test_slots_never_sit_on_top_of_each_other(display, slots):
    made = SceneStack(Viewport(WINDOW))
    play = GameplayScene(made.window, made.manager)
    made.push(play)
    play.session.backpack.resize(slots)
    try:
        screen = packfront.BackpackScreen(made.window, made.manager, play.session)
        made.push(screen)
        boxes = [*screen.slots, *screen.hands]
        for index, box in enumerate(boxes):
            for other in boxes[index + 1 :]:
                assert not box.colliderect(other), (box, other)
    finally:
        made.clear()


def test_a_bigger_pack_shrinks_its_slots_rather_than_refusing(display):
    made = SceneStack(Viewport(WINDOW))
    play = GameplayScene(made.window, made.manager)
    made.push(play)
    try:
        play.session.backpack.resize(12)
        made.push(packfront.BackpackScreen(made.window, made.manager, play.session))
        roomy = made.top.slots[0].width
        made.pop()

        play.session.backpack.resize(items.MOST_SLOTS)
        made.push(packfront.BackpackScreen(made.window, made.manager, play.session))

        assert made.top.slots[0].width < roomy
    finally:
        made.clear()


def test_slots_are_as_big_as_the_room_allows(display):
    """Shrinking is a last resort, not the first answer. Falling straight to
    the smallest size fits just as well and looks far worse, so nothing would
    have caught it."""
    made = SceneStack(Viewport(WINDOW))
    play = GameplayScene(made.window, made.manager)
    made.push(play)
    sizes = {}
    try:
        for slots in (12, 24, items.MOST_SLOTS):
            play.session.backpack.resize(slots)
            made.push(packfront.BackpackScreen(made.window, made.manager, play.session))
            sizes[slots] = made.top.slots[0].width
            made.pop()
    finally:
        made.clear()

    assert sizes[12] == packfront.SLOT, "a small pack has no reason to shrink"
    assert sizes[12] > sizes[24] > sizes[items.MOST_SLOTS]
