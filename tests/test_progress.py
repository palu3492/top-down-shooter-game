"""Progress that survives closing the game.

The half of the campaign problem that is a handful of numbers. What matters is
that it comes back, that a corrupt or stale file cannot stop the game starting,
and that nothing the player has earned can move backwards.
"""

import json
from pathlib import Path

import pygame
import pygame_gui
import pytest

from shooter import game, session
from shooter.progress import FIRST_LEVEL, Progress, progress_path
from shooter.scenes import SceneStack
from shooter.settings import Settings
from shooter.systems import levels
from shooter.ui import menu, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)
LAST = levels.LEVELS[-1].number


@pytest.fixture
def progress(tmp_path):
    return Progress(path=tmp_path / "progress.json", last_level=LAST)


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    yield made
    made.clear()


def route(stack, action, progress=None):
    return game.route(action, stack, stack.window, Settings(), progress)


def press(stack, label, progress=None):
    button = next(w for w, a in stack.top.actions.items() if a == label)
    return route(
        stack,
        stack.top.handle(
            pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button)
        ),
        progress,
    )


# ----------------------------------------------------------------------
# The store
# ----------------------------------------------------------------------


def test_a_new_player_starts_at_the_beginning(progress):
    assert progress.reached == FIRST_LEVEL
    assert progress.completed == ()
    assert progress.started is False


def test_finishing_a_level_opens_the_next(progress):
    progress.record(1)
    assert progress.completed == (1,)
    assert progress.reached == 2
    assert progress.started is True


def test_progress_survives_the_game_closing(progress):
    progress.record(1)
    progress.record(2)
    progress.save()

    reopened = Progress(path=progress.path, last_level=LAST)
    assert reopened.load() == ()
    assert reopened.reached == 3
    assert reopened.completed == (1, 2)


def test_nothing_earned_moves_backwards(progress):
    """Replaying an early level must not take away a level already reached."""
    progress.record(3)
    assert progress.reached == 4

    progress.record(1)

    assert progress.reached == 4
    assert progress.completed == (1, 3)


def test_a_level_finished_twice_is_recorded_once(progress):
    progress.record(2)
    progress.record(2)
    assert progress.completed == (2,)


def test_the_campaign_cannot_unlock_past_its_last_level(progress):
    progress.record(LAST)
    assert progress.reached == LAST
    assert progress.finished is True


def test_a_missing_file_is_not_an_error(tmp_path):
    fresh = Progress(path=tmp_path / "never" / "written.json", last_level=LAST)
    assert fresh.load() == ()
    assert fresh.reached == FIRST_LEVEL


def test_a_corrupt_file_starts_from_the_beginning(progress):
    progress.path.parent.mkdir(parents=True, exist_ok=True)
    progress.path.write_text("{ not json")

    assert progress.load() == ()
    assert progress.reached == FIRST_LEVEL


def test_a_file_that_is_not_an_object_starts_from_the_beginning(progress):
    progress.path.parent.mkdir(parents=True, exist_ok=True)
    progress.path.write_text("[1, 2, 3]")
    assert progress.load() == ()
    assert progress.reached == FIRST_LEVEL


def test_a_stale_file_is_clamped_rather_than_refused(progress):
    """A save from a build with more levels is not a reason to refuse to
    start; it is a reason to start at the last level there is."""
    progress.path.parent.mkdir(parents=True, exist_ok=True)
    progress.path.write_text(json.dumps({"reached": 99, "completed": [1, 99]}))

    rejected = progress.load()

    assert progress.reached == LAST
    assert 99 not in progress.completed
    assert set(rejected) == {"reached", "completed"}


def test_rubbish_values_are_named_and_the_rest_still_load(progress):
    progress.path.parent.mkdir(parents=True, exist_ok=True)
    progress.path.write_text(json.dumps({"reached": "three", "completed": [1, 2]}))

    assert progress.load() == ("reached",)
    assert progress.completed == (1, 2)


def test_true_is_not_a_level_number(progress):
    """`True` is an int in Python, so it has to be turned away explicitly."""
    progress.path.parent.mkdir(parents=True, exist_ok=True)
    progress.path.write_text(json.dumps({"reached": True, "completed": [True]}))

    progress.load()

    assert progress.reached == FIRST_LEVEL
    assert progress.completed == ()


def test_an_interrupted_save_leaves_the_previous_progress(progress, monkeypatch):
    progress.record(2)
    progress.save()

    def die(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("json.dump", die)
    progress.record(3)
    with pytest.raises(OSError):
        progress.save()

    reopened = Progress(path=progress.path, last_level=LAST)
    reopened.load()
    assert reopened.reached == 3
    assert list(progress.path.parent.glob("*.tmp")) == []


def test_progress_lives_outside_the_repository():
    path = progress_path()
    assert path.name == "progress.json"
    assert Path.cwd() not in path.parents


def test_progress_sits_beside_the_settings():
    from shooter.settings import settings_path

    assert progress_path().parent == settings_path().parent


# ----------------------------------------------------------------------
# Through the game
# ----------------------------------------------------------------------


def test_a_fresh_menu_offers_no_way_to_continue(stack, progress):
    stack.push(title.MainMenuScene(stack.window, stack.manager, progress))
    assert title.CONTINUE not in [action for _, action in stack.top.entries]
    assert title.START in [action for _, action in stack.top.entries]


def test_a_returning_player_is_offered_the_level_they_reached(stack, progress):
    progress.record(2)
    stack.push(title.MainMenuScene(stack.window, stack.manager, progress))

    labels = {action: label for label, action in stack.top.entries}

    assert title.CONTINUE in labels
    assert "LEVEL 3" in labels[title.CONTINUE]
    assert title.START in labels, "starting over is still offered"


def test_continue_starts_the_level_that_was_reached(stack, progress):
    progress.record(2)
    stack.push(title.MainMenuScene(stack.window, stack.manager, progress))

    press(stack, title.CONTINUE, progress)

    assert stack.top.session.rules.level.number == 3


def test_winning_a_level_is_written_to_disk(stack, progress):
    stack.push(title.MainMenuScene(stack.window, stack.manager, progress))
    route(stack, title.START, progress)
    stack.top.session.rules.cleared = stack.top.session.rules.level.waves

    route(stack, stack.top.tick(1 / 60), progress)

    assert progress.completed == (1,)
    assert json.loads(progress.path.read_text())["reached"] == 2


def test_losing_a_level_is_not_written_down(stack, progress):
    stack.push(title.MainMenuScene(stack.window, stack.manager, progress))
    route(stack, title.START, progress)
    scene = stack.top
    scene.session.human.remove_health(1000)
    scene.session.human.kill()

    route(stack, scene.tick(1 / 60), progress)

    assert progress.completed == ()
    assert not progress.path.exists()


def test_a_game_played_without_progress_still_works(stack):
    """`route` is called with no progress in plenty of tests, and a win must
    not fall over because nothing is keeping score."""
    stack.push(title.MainMenuScene(stack.window, stack.manager))
    route(stack, title.START)
    stack.top.session.rules.cleared = stack.top.session.rules.level.waves

    route(stack, stack.top.tick(1 / 60))

    assert isinstance(stack.top, menu.ResultScreen)
    assert stack.top.outcome == session.WON
