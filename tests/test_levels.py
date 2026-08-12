"""Freeplay as numbered levels.

The test worth having is that a level can be *finished* -- clearing every wave
in order and arriving at a win. Everything else is arithmetic about how many
zombies arrive when.
"""

import pygame
import pytest

from shooter import config, game, session
from shooter.gameplay import GameplayScene
from shooter.scenes import SceneStack
from shooter.settings import Settings
from shooter.systems import levels
from shooter.ui import menu, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    made.push(title.MainMenuScene(made.window, made.manager))
    yield made
    made.clear()


@pytest.fixture
def rules(display, cash):
    group = pygame.sprite.Group()
    return levels.LevelRules(WINDOW, group, cash), group


def route(stack, action):
    return game.route(action, stack, stack.window, Settings())


def press(stack, label):
    import pygame_gui

    button = next(w for w, a in stack.top.actions.items() if a == label)
    return route(
        stack,
        stack.top.handle(
            pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
        ),
    )


def clear_a_wave(rules, group, cash):
    """Kill everything, then let the between-wave timer run out."""
    group.empty()
    rules.advance(WINDOW, group, cash, config.WAVE_INTERVAL_SECONDS)
    rules.advance(WINDOW, group, cash, config.SIM_DT)


# ----------------------------------------------------------------------
# The table
# ----------------------------------------------------------------------


def test_levels_are_numbered_from_one_without_gaps():
    assert [level.number for level in levels.LEVELS] == list(
        range(1, len(levels.LEVELS) + 1)
    )


def test_each_level_asks_for_more_than_the_last():
    for earlier, later in zip(levels.LEVELS, levels.LEVELS[1:], strict=False):
        assert later.waves >= earlier.waves
        assert later.opening > earlier.opening


def test_freeplay_does_not_run_out_of_levels():
    """Past the authored ones the hardest is played again, rather than the game
    refusing to start."""
    assert levels.level_number(1) is levels.LEVELS[0]
    assert levels.level_number(99) is levels.LEVELS[-1]


# ----------------------------------------------------------------------
# Playing one
# ----------------------------------------------------------------------


def test_a_level_opens_with_its_own_wave_size(rules):
    ruleset, group = rules
    assert len(group) == ruleset.level.opening


def test_a_level_is_not_won_before_it_is_played(rules):
    ruleset, _ = rules
    assert ruleset.outcome is None


def test_each_wave_is_bigger_than_the_last(rules, cash):
    ruleset, group = rules
    sizes = [len(group)]

    for _ in range(ruleset.level.waves - 1):
        clear_a_wave(ruleset, group, cash)
        sizes.append(len(group))

    assert sizes == sorted(sizes)
    assert sizes[-1] > sizes[0]


def test_clearing_every_wave_wins_the_level(rules, cash):
    """The whole point: a level can be finished."""
    ruleset, group = rules

    for wave in range(ruleset.level.waves):
        assert ruleset.outcome is None, f"won early, on wave {wave + 1}"
        clear_a_wave(ruleset, group, cash)

    assert ruleset.outcome == session.WON


def test_a_won_level_stops_spawning(rules, cash):
    ruleset, group = rules
    for _ in range(ruleset.level.waves):
        clear_a_wave(ruleset, group, cash)

    group.empty()
    for _ in range(10):
        clear_a_wave(ruleset, group, cash)

    assert len(group) == 0, "the level kept going after it was won"


def test_the_wave_counter_stops_at_the_target(rules, cash):
    ruleset, group = rules
    for _ in range(ruleset.level.waves + 3):
        clear_a_wave(ruleset, group, cash)
    assert ruleset.wave == ruleset.level.waves


# ----------------------------------------------------------------------
# Through a session
# ----------------------------------------------------------------------


def test_starting_a_game_plays_the_first_level(stack):
    route(stack, title.START)

    assert isinstance(stack.top, GameplayScene)
    assert stack.top.session.rules.level is levels.FIRST


def test_winning_names_the_level(stack):
    route(stack, title.START)
    scene = stack.top
    scene.session.rules.cleared = scene.session.rules.level.waves

    route(stack, scene.tick(1 / 60))

    assert stack.top.title == "LEVEL 1 COMPLETE"


def test_winning_offers_the_way_onward(stack):
    route(stack, title.START)
    stack.top.session.rules.cleared = stack.top.session.rules.level.waves
    route(stack, stack.top.tick(1 / 60))

    assert menu.NEXT_LEVEL in [action for _, action in stack.top.entries]
    assert menu.RETRY not in [action for _, action in stack.top.entries]


def test_losing_offers_the_way_back(stack):
    route(stack, title.START)
    stack.top.session.human.remove_health(config.PLAYER_HEALTH)
    stack.top.session.human.kill()
    route(stack, stack.top.tick(1 / 60))

    assert menu.RETRY in [action for _, action in stack.top.entries]
    assert menu.NEXT_LEVEL not in [action for _, action in stack.top.entries]


def test_next_level_plays_the_next_one(stack):
    route(stack, title.START)
    stack.top.session.rules.cleared = stack.top.session.rules.level.waves
    route(stack, stack.top.tick(1 / 60))

    press(stack, menu.NEXT_LEVEL)

    assert isinstance(stack.top, GameplayScene)
    assert stack.top.session.rules.level.number == 2
    assert len(stack) == 2, "the main menu is still underneath"


def test_retry_replays_the_level_that_was_lost(stack):
    route(stack, title.START)
    route(stack, menu.NEXT_LEVEL)  # move on to level two
    assert stack.top.session.rules.level.number == 2

    stack.top.session.human.remove_health(config.PLAYER_HEALTH)
    stack.top.session.human.kill()
    route(stack, stack.top.tick(1 / 60))
    press(stack, menu.RETRY)

    assert stack.top.session.rules.level.number == 2, "retry sent us back to level one"


def test_the_last_level_repeats_rather_than_running_out(stack):
    route(stack, title.START)
    last = levels.LEVELS[-1]
    game.start_level(stack, stack.window, last, replacing=1)
    stack.top.session.rules.cleared = last.waves

    route(stack, stack.top.tick(1 / 60))
    press(stack, menu.NEXT_LEVEL)

    assert stack.top.session.rules.level is last


def test_a_level_is_won_by_playing_it(display):
    """Driven through `Session.step` rather than by setting counters, so the
    win arrives the way it will in a real game: waves clear, the timer runs
    out, and eventually there is nothing left to send."""
    from shooter.session import Session

    played = levels.LEVELS[0]
    game_session = Session(Viewport(WINDOW), rules=levels.rules_for(played))
    idle = dict.fromkeys(range(512), False)
    waves_seen = 0

    for _ in range(20_000):
        if game_session.outcome is not None:
            break
        if game_session.zombies:
            game_session.zombies.empty()
            waves_seen += 1
        game_session.step(idle, config.SIM_DT)

    assert game_session.outcome == session.WON
    assert waves_seen == played.waves, (
        f"expected {played.waves} waves, fought {waves_seen}"
    )
    assert game_session.human.alive(), "nothing should have killed the player"
