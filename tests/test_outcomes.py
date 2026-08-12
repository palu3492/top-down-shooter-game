"""A game that can be over.

Before this, `human.kill()` fired and nothing responded: three hundred steps
later the zombies were still converging on a body and the wave timer was still
counting. Levels and campaign progress both mean *a level is completed*, so
neither could be built until finishing meant something.
"""

import pygame
import pytest

from shooter import config, game, session
from shooter.gameplay import GameplayScene
from shooter.scenes import SceneStack
from shooter.settings import Settings
from shooter.systems.waves import WaveSystem
from shooter.ui import menu, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)


class WinnableRules(WaveSystem):
    """A mode with a finish line, which is all AT34 will be."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcome = None

    def win(self):
        self.outcome = session.WON


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    made.push(title.MainMenuScene(made.window, made.manager))
    yield made
    made.clear()


@pytest.fixture
def playing(stack):
    scene = GameplayScene(stack.window, stack.manager)
    stack.push(scene)
    return scene


def route(stack, action):
    return game.route(action, stack, stack.window, Settings())


def kill(scene):
    scene.session.human.remove_health(config.PLAYER_HEALTH)
    scene.session.human.kill()


def press(stack, label):
    button = next(w for w, a in stack.top.actions.items() if a == label)
    import pygame_gui

    return route(
        stack,
        stack.top.handle(
            pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
        ),
    )


# ----------------------------------------------------------------------
# The session
# ----------------------------------------------------------------------


def test_a_game_being_played_has_no_outcome(playing):
    assert playing.session.outcome is None


def test_a_dead_player_has_lost(playing):
    kill(playing)
    assert playing.session.outcome == session.LOST


def test_endless_freeplay_never_declares_a_win(playing):
    """There is no finish line, so a game can only end by being lost."""
    assert playing.session.rules.outcome is None
    for _ in range(200):
        playing.session.step(dict.fromkeys(range(512), False), config.SIM_DT)
    assert playing.session.outcome is None


def test_winning_comes_from_the_rules(display, stack):
    """Losing is the session's business whatever the mode; what counts as
    finished is exactly what a mode decides."""
    scene = GameplayScene(stack.window, stack.manager, rules=WinnableRules)
    stack.push(scene)

    assert scene.session.outcome is None
    scene.session.rules.win()
    assert scene.session.outcome == session.WON


def test_losing_beats_winning(display, stack):
    """A player who dies has lost even if the rules were about to be satisfied."""
    scene = GameplayScene(stack.window, stack.manager, rules=WinnableRules)
    stack.push(scene)
    scene.session.rules.win()
    kill(scene)

    assert scene.session.outcome == session.LOST


# ----------------------------------------------------------------------
# Reporting it
# ----------------------------------------------------------------------


def test_an_ending_is_reported_once(playing):
    """The outcome stays true for every frame after it happens, so without a
    guard the shell would be handed a result screen sixty times a second."""
    kill(playing)

    assert playing.tick(1 / 60) == session.LOST
    assert [playing.tick(1 / 60) for _ in range(60)] == [None] * 60


def test_nothing_is_reported_while_the_game_is_being_played(playing):
    assert [playing.tick(1 / 60) for _ in range(10)] == [None] * 10


# ----------------------------------------------------------------------
# What the player sees
# ----------------------------------------------------------------------


def test_dying_puts_a_result_screen_up(stack, playing):
    kill(playing)
    route(stack, playing.tick(1 / 60))

    assert isinstance(stack.top, menu.ResultScreen)
    assert stack.top.title == "YOU DIED"


def test_winning_says_so(display, stack):
    scene = GameplayScene(stack.window, stack.manager, rules=WinnableRules)
    stack.push(scene)
    scene.session.rules.win()

    route(stack, scene.tick(1 / 60))

    assert stack.top.title == "LEVEL COMPLETE"


def test_the_world_stops_once_the_game_is_over(stack, playing):
    kill(playing)
    route(stack, playing.tick(1 / 60))

    before = [z.get_position() for z in playing.session.zombies]
    for _ in range(30):
        stack.update(
            game.Inputs(dict.fromkeys(range(512), False), (0, 0)), config.SIM_DT
        )

    assert stack.simulates is False
    assert [z.get_position() for z in playing.session.zombies] == before, (
        "the zombies were still closing in on a body"
    )


def test_the_result_screen_shows_the_world_behind_it(stack, playing):
    kill(playing)
    route(stack, playing.tick(1 / 60))

    assert stack.top.opaque is False
    assert stack.visible() == [playing, stack.top]


def test_escape_does_not_dismiss_a_finished_game(stack, playing):
    """There is nothing to go back to, and closing it would leave a finished
    game running underneath."""
    kill(playing)
    route(stack, playing.tick(1 / 60))

    escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert stack.top.handle(escape) is None
    assert isinstance(stack.top, menu.ResultScreen)


# ----------------------------------------------------------------------
# What happens next
# ----------------------------------------------------------------------


def test_retry_starts_a_fresh_game(stack, playing):
    playing.session.cash.increase_cash(900)
    kill(playing)
    route(stack, playing.tick(1 / 60))

    press(stack, menu.RETRY)

    assert isinstance(stack.top, GameplayScene)
    assert stack.top is not playing
    assert stack.top.session.cash.cash_amount == 0
    assert stack.top.session.outcome is None
    assert len(stack) == 2, "the main menu is still underneath"


def test_the_main_menu_is_reachable_from_a_finished_game(stack, playing):
    kill(playing)
    route(stack, playing.tick(1 / 60))

    press(stack, menu.END_GAME)

    assert isinstance(stack.top, title.MainMenuScene)
    assert len(stack) == 1


def test_ending_a_game_from_pause_still_works(stack, playing):
    """END GAME now pops whatever is above the menu rather than exactly two
    scenes, so it has to keep working from the pause screen it came from."""
    route(stack, game.PAUSE)
    assert isinstance(stack.top, menu.PauseScreen)

    press(stack, menu.END_GAME)

    assert isinstance(stack.top, title.MainMenuScene)
    assert len(stack) == 1


def test_quitting_from_a_finished_game_stops_the_game(stack, playing):
    kill(playing)
    route(stack, playing.tick(1 / 60))
    assert press(stack, menu.QUIT) is False
