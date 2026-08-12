import os
import subprocess
import sys
from pathlib import Path

import pygame
import pytest

from shooter.entities import projectiles
from shooter.game import game_loop

REPO = Path(__file__).resolve().parent.parent


def run_isolated(code, **env_overrides):
    """Run code in a fresh interpreter so import-time effects are observable.

    Inherits this process's environment, which conftest has already pointed at
    the dummy SDL drivers; PYTHONPATH is added because pytest's `pythonpath`
    setting only affects the collecting process, not subprocesses.
    """
    env = {**os.environ, "PYTHONPATH": str(REPO), **env_overrides}
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=REPO
    )


def test_importing_projectiles_has_no_side_effects():
    result = run_isolated(
        "import pygame\n"
        "import shooter.entities.projectiles\n"
        "assert pygame.mixer.get_init() is None, 'import initialised the mixer'\n"
        "print('clean')"
    )

    assert result.returncode == 0, result.stderr
    assert "clean" in result.stdout


def test_the_game_starts_without_a_usable_audio_device():
    result = run_isolated(
        "import pygame\n"
        "from shooter.entities.projectiles import play, GUN_SHOT\n"
        "pygame.init()\n"
        "assert pygame.mixer.get_init() is None\n"
        "play(GUN_SHOT)\n"
        "print('survived')",
        SDL_AUDIODRIVER="nonsense",
    )

    assert result.returncode == 0, result.stderr
    assert "survived" in result.stdout


def test_sounds_still_play_when_audio_is_available():
    assert pygame.mixer.get_init() is not None
    projectiles.play(projectiles.GUN_SHOT)
    projectiles.play(projectiles.EXPLOSION)

    assert projectiles._load.cache_info().currsize == 2


def quit_after(frames, event):
    """Let the loop run, then post `event` so it exits through its own path."""
    counter = iter(range(frames + 1))
    real_flip = pygame.display.flip

    def flip():
        if next(counter, frames) >= frames:
            pygame.event.post(pygame.event.Event(event))
        real_flip()

    return flip


@pytest.mark.parametrize("frames", [1, 30])
def test_game_loop_returns_on_quit_event(monkeypatch, frames):
    monkeypatch.setattr(pygame.display, "flip", quit_after(frames, pygame.QUIT))

    game_loop()

    assert pygame.display.get_init() is False


def press(*keys):
    """Post a KEYDOWN for each key, one per frame, then stop."""
    queued = list(keys)
    real_flip = pygame.display.flip
    frames = iter(range(10_000))

    def flip():
        n = next(frames)
        if n >= 20 and n % 5 == 0 and queued:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=queued.pop(0)))
        real_flip()

    return flip


def test_escape_then_q_leaves_the_game(monkeypatch):
    monkeypatch.setattr(pygame.display, "flip", press(pygame.K_ESCAPE, pygame.K_q))

    game_loop()

    assert pygame.display.get_init() is False


def test_q_alone_does_not_quit_while_playing(monkeypatch):
    monkeypatch.setattr(
        pygame.display, "flip", press(pygame.K_q, pygame.K_ESCAPE, pygame.K_q)
    )

    game_loop()

    assert pygame.display.get_init() is False
