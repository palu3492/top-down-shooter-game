"""Pause behavior expressed through authoritative simulation state."""

import pytest

from shooter import config
from shooter.game import advance_simulation
from shooter.gameplay import GameplayScene
from shooter.scenes import SceneStack
from shooter.ui.menu import PauseScreen
from shooter.viewport import Viewport
from shooter.weapons import M16, equip

WINDOW = (1080, 720)


@pytest.fixture
def stack(display):
    made = SceneStack(Viewport(WINDOW))
    yield made
    made.clear()


def reloading_game(stack):
    playing = GameplayScene(stack.window, stack.manager)
    stack.push(playing)
    gun = equip(M16)
    gun.loaded = 0
    gun.manual_reload()
    playing.session.carried = [gun]
    playing.session.equipped = gun
    return playing, gun


def test_pause_freezes_authoritative_state_and_resume_continues_it(
    stack, input_frame
):
    playing, gun = reloading_game(stack)
    session = playing.session
    locked_for = gun.locked_for

    stack.push(PauseScreen(stack.window, stack.manager))
    remainder = advance_simulation(stack, input_frame(), accumulator=10.0)

    assert remainder == 0.0
    assert gun.locked_for == locked_for

    stack.pop()
    remainder = advance_simulation(stack, input_frame(), accumulator=config.SIM_DT)

    assert stack.top is playing
    assert stack.top.session is session
    assert gun.locked_for == pytest.approx(locked_for - config.SIM_DT)
    assert remainder == pytest.approx(0.0)


def test_paused_wall_time_cannot_become_resume_steps(input_frame):
    class CountingScenes:
        simulates = False

        def __init__(self):
            self.steps = 0

        def update(self, inputs, dt):
            self.steps += 1

    scenes = CountingScenes()

    remainder = advance_simulation(scenes, input_frame(), accumulator=60.0)
    scenes.simulates = True
    remainder = advance_simulation(
        scenes,
        input_frame(),
        accumulator=remainder + config.SIM_DT,
    )

    assert scenes.steps == 1
    assert remainder == pytest.approx(0.0)


def test_pause_characterization_does_not_depend_on_animation_counts(
    stack, input_frame, monkeypatch
):
    playing, gun = reloading_game(stack)

    def animation_must_not_be_the_clock(*args, **kwargs):
        raise AssertionError("pause characterization touched presentation animation")

    monkeypatch.setattr(
        playing.session.human,
        "update_anim",
        animation_must_not_be_the_clock,
    )
    stack.push(PauseScreen(stack.window, stack.manager))

    advance_simulation(stack, input_frame(), accumulator=5.0)

    assert gun.locked_for == config.RELOAD_SECONDS
