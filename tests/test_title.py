"""Splash, main menu, and the shape of a session's life.

Starting a game and ending one are the point. Everything else here exists to
make sure the flow cannot get stuck: the splash always hands over, the menu is
still underneath a game, and ending one finds it where it was left.
"""

import pygame
import pygame_gui
import pytest

from shooter import config, game
from shooter.gameplay import GameplayScene
from shooter.scenes import SceneStack
from shooter.settings import Settings
from shooter.ui import menu, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    yield made
    made.clear()


@pytest.fixture
def booted(stack):
    stack.push(title.SplashScene(stack.window, stack.manager))
    return stack


def route(stack, action):
    return game.route(action, stack, stack.window, Settings())


def reach_the_menu(stack):
    route(stack, stack.top.tick(title.FADE_IN + title.HOLD))
    return stack.top


def press(stack, label):
    button = next(
        widget for widget, action in stack.top.actions.items() if action == label
    )
    pressed = pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
    return route(stack, stack.top.handle(pressed))


# ----------------------------------------------------------------------
# The splash
# ----------------------------------------------------------------------


def test_the_splash_hands_over_on_its_own(booted):
    assert booted.top.tick(0.1) is None
    assert booted.top.tick(title.FADE_IN + title.HOLD) == title.MENU


def test_the_splash_fades_up_rather_than_appearing(booted):
    splash = booted.top
    assert splash.brightness == 0.0
    splash.tick(title.FADE_IN / 2)
    assert 0.4 < splash.brightness < 0.6
    splash.tick(title.FADE_IN)
    assert splash.brightness == 1.0


def test_the_splash_can_be_skipped(booted):
    booted.top.tick(title.SKIPPABLE_AFTER + 0.01)
    action = booted.top.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    assert action == title.MENU


def test_the_splash_ignores_a_key_it_has_not_had_time_to_show(booted):
    """A key already down when the game launches should not blow straight
    through the title card."""
    action = booted.top.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    assert action is None


def test_the_splash_is_replaced_rather_than_covered(booted):
    reach_the_menu(booted)
    assert len(booted) == 1
    assert isinstance(booted.top, title.MainMenuScene)


# ----------------------------------------------------------------------
# Starting and ending a game
# ----------------------------------------------------------------------


def test_start_puts_a_game_on_top_of_the_menu(booted):
    reach_the_menu(booted)
    press(booted, title.START)

    assert isinstance(booted.top, GameplayScene)
    assert len(booted) == 2, "the menu is still underneath"
    assert booted.simulates is True


def test_ending_a_game_finds_the_menu_where_it_was_left(booted):
    reach_the_menu(booted)
    press(booted, title.START)
    route(booted, game.PAUSE)
    assert isinstance(booted.top, menu.PauseScreen)

    press(booted, menu.END_GAME)

    assert isinstance(booted.top, title.MainMenuScene)
    assert len(booted) == 1
    assert booted.simulates is False


def test_a_game_started_after_ending_one_owes_it_nothing(booted):
    reach_the_menu(booted)
    press(booted, title.START)
    booted.top.session.cash.increase_cash(750)
    route(booted, game.PAUSE)
    press(booted, menu.END_GAME)

    press(booted, title.START)

    assert booted.top.session.cash.cash_amount == 0


def test_the_menu_offers_a_way_to_start_and_a_way_out(booted):
    actions = [action for _, action in reach_the_menu(booted).entries]
    assert title.START in actions
    assert menu.QUIT in actions


def test_pause_offers_a_way_back_to_the_menu(window, stack):
    assert menu.END_GAME in [
        action for _, action in menu.PauseScreen(window, stack.manager).entries
    ]


def test_quitting_from_the_menu_stops_the_game(booted):
    reach_the_menu(booted)
    assert press(booted, menu.QUIT) is False


# ----------------------------------------------------------------------
# Wall time is not the simulation clock
# ----------------------------------------------------------------------


def test_the_splash_animates_while_nothing_simulates(booted):
    """`update` never runs for an interface scene, so a splash driven by it
    would sit on its first frame forever."""
    assert booted.simulates is False

    booted.update(game.Inputs(dict.fromkeys(range(512), False), (0, 0)), config.SIM_DT)
    assert booted.top.elapsed == 0.0

    booted.tick(0.5)
    assert booted.top.elapsed == 0.5


def test_the_interface_is_given_real_elapsed_time(booted, monkeypatch):
    """pygame_gui used to be handed a constant 1/60 from inside `draw`, so its
    own animations ran at the wrong rate on any machine not managing sixty."""
    seen = []
    monkeypatch.setattr(booted.manager, "update", seen.append)

    booted.tick(0.037)

    assert seen == [0.037]


def test_drawing_does_not_advance_the_splash(booted):
    surface = pygame.Surface(WINDOW)
    booted.tick(0.2)
    before = booted.top.elapsed

    for _ in range(5):
        booted.draw(surface, 0.0)

    assert booted.top.elapsed == before


# ----------------------------------------------------------------------
# The backdrop
# ----------------------------------------------------------------------


def test_the_backdrop_is_built_once_per_size(display):
    """It smoothscales a 4961x2481 image; once a frame would be a fifth of a
    second of work per frame."""
    assert title.backdrop(WINDOW) is title.backdrop(WINDOW)
    assert title.backdrop((1920, 1080)) is not title.backdrop(WINDOW)


def test_the_backdrop_fills_the_window(display):
    assert title.backdrop(WINDOW).get_size() == WINDOW
    assert title.backdrop((1920, 1080)).get_size() == (1920, 1080)


def test_the_whole_scene_survives_the_aspect_difference(display):
    """The art is 2:1 and the window is 3:2. Cropping to fill would cut the
    shooter off the left edge, so it is scaled to width and sat on the ground."""
    surface = title.backdrop(WINDOW)
    sky = surface.get_at((0, 0))
    art = title.load_image(title.ART)
    assert (
        sky[:3]
        == pygame.transform.smoothscale(art, (WINDOW[0], 540)).get_at((0, 0))[:3]
    )


# ----------------------------------------------------------------------
# Pixel art
# ----------------------------------------------------------------------


def test_the_backdrop_is_a_baked_asset_not_a_computed_one(display):
    """Mapping the painting to a palette is a nearest-colour search per pixel
    -- about a second, which AT28 spent a whole ticket making sure nothing does
    at startup. `tools/make_menu_art.py` does it once, offline."""
    art = title.load_image(title.ART)
    assert art.get_size() == (135, 90), "the source is small on purpose"
    assert title.ART.endswith("menu_pixel.png")


def test_the_art_uses_a_small_palette(display):
    """What makes it read as pixel art rather than a photograph shown too
    small. Pixelating alone leaves soft blocks, because they are soft blocks."""
    art = title.load_image(title.ART)
    colours = {art.get_at((x, y))[:3] for x in range(135) for y in range(90)}
    assert len(colours) <= 8, sorted(colours)


def test_the_backdrop_keeps_its_pixels_square(display):
    """Interpolating pixel art is precisely what stops it looking like pixel
    art, so this scales with nearest-neighbour."""
    art = title.load_image(title.ART)
    blown = title.backdrop((1080, 720))

    assert blown.get_size() == (1080, 720)
    assert {blown.get_at((x, y))[:3] for x in range(1080) for y in (0, 400, 719)} <= {
        art.get_at((x, y))[:3] for x in range(135) for y in range(90)
    }


def test_the_default_resolution_gets_whole_blocks(display):
    """135x90 is exactly an eighth of 1080x720."""
    art = title.load_image(title.ART)
    assert 1080 % art.get_width() == 0
    assert 720 % art.get_height() == 0


def test_pixel_text_has_no_antialiasing_ramp(display):
    """Rendered small with antialiasing off, then blown up square.

    The ramp a smoothed font leaves lives in the alpha channel, so both have to
    be laid on something opaque before the shades can be counted.
    """

    def shades(text):
        plate = pygame.Surface(text.get_size())
        plate.fill((0, 0, 0))
        plate.blit(text, (0, 0))
        return {
            plate.get_at((x, y))[:3]
            for x in range(plate.get_width())
            for y in range(plate.get_height())
        }

    chunky = shades(title.pixel_text("ABC", 64, title.INK))
    smooth = shades(pygame.font.Font(None, 64).render("ABC", True, title.INK))

    assert len(chunky) == 2, f"ink and background, nothing between: {chunky}"
    assert len(smooth) > 10, "the smooth one ramps, which is the point"


def test_pixel_text_stays_the_size_it_was_asked_for(display):
    """The scale changes how chunky the letters are, not how big they come out."""
    fine = title.pixel_text("ABC", 64, title.INK, 2)
    chunky = title.pixel_text("ABC", 64, title.INK, 8)
    assert abs(fine.get_width() - chunky.get_width()) < fine.get_width() // 3


def test_pixel_text_is_cached(display):
    assert title.pixel_text("HELLO", 40, title.INK) is title.pixel_text(
        "HELLO", 40, title.INK
    )


def test_the_interface_font_is_not_antialiased(display):
    """The buttons sit on pixel art; a smoothed font fights it."""
    from shooter.scenes import build_manager

    theme = build_manager((1080, 720)).get_theme()
    for element in ("button", "label", "check_box"):
        assert theme.get_font_info([element])["antialiased"] is False, element


def test_the_theme_still_loads_without_complaint(display):
    """pygame_gui warns rather than raises on a malformed block -- a font
    without a size, an object id it cannot resolve -- so the warnings are the
    assertion."""
    import warnings

    from shooter.scenes import build_manager

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        build_manager((1080, 720))
