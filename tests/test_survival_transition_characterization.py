"""Current Survival field-clear, preparation, and next-wave behavior."""

import pygame
import pytest

from shooter import config
from shooter.session import Session
from shooter.viewport import Viewport

WINDOW = (1080, 720)


def survival_session(monkeypatch):
    monkeypatch.setattr(config, "ZOMBIE_SPAWNING_ENABLED", True)
    return Session(Viewport(WINDOW))


def test_preparation_does_not_advance_while_an_enemy_remains(
    monkeypatch, input_frame, advance_steps
):
    session = survival_session(monkeypatch)

    advance_steps(lambda dt: session.step(input_frame().pressed, dt), 12)

    assert session.zombies
    assert session.rules.wave_seconds == 0.0
    assert session.rules.wave_count == 0


def test_removing_the_last_enemy_begins_one_preparation_timer(
    monkeypatch, input_frame
):
    session = survival_session(monkeypatch)
    for enemy in session.zombies:
        enemy.kill()

    session.step(input_frame().pressed)

    assert not session.zombies
    assert session.rules.wave_seconds == pytest.approx(config.SIM_DT)
    assert session.rules.wave_count == 0


def test_preparation_advances_once_per_fixed_step(
    monkeypatch, input_frame, advance_steps
):
    session = survival_session(monkeypatch)
    session.zombies.empty()

    elapsed = advance_steps(
        lambda dt: session.step(input_frame().pressed, dt),
        12,
    )

    assert session.rules.wave_seconds == pytest.approx(elapsed)
    assert session.rules.wave_count == 0


def test_timer_completion_requests_exactly_one_next_wave(monkeypatch, input_frame):
    session = survival_session(monkeypatch)
    session.zombies.empty()
    session.rules.wave_seconds = config.WAVE_INTERVAL_SECONDS

    session.step(input_frame().pressed)

    assert session.rules.wave_count == 1
    assert session.rules.wave_seconds == 0.0
    assert session.zombies
    arrived = set(session.zombies)

    session.step(input_frame().pressed)

    assert session.rules.wave_count == 1
    assert set(session.zombies) == arrived


def test_space_is_an_explicit_one_step_skip_request(monkeypatch, input_frame):
    session = survival_session(monkeypatch)
    session.zombies.empty()

    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    session.step(input_frame().pressed)

    assert session.rules.wave_count == 1
    assert session.rules.wave_seconds == 0.0
    assert session.zombies
