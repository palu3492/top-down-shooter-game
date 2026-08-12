import pygame
import pytest

from shooter import game

CAP = 400


class LoopRanAwayError(Exception):
    pass


def drive(script, monkeypatch):
    """Post one KEYDOWN per script entry, every 5 frames after a warm-up.

    Hard-capped: a game_loop that never exits raises instead of hanging.
    """
    queued = list(script)
    real_flip = pygame.display.flip
    counter = {"n": 0}

    def flip():
        counter["n"] += 1
        n = counter["n"]
        if n > CAP:
            raise LoopRanAwayError(f"game_loop still running after {CAP} frames")
        if n >= 20 and n % 5 == 0 and queued:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=queued.pop(0)))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    return counter


def test_pause_resume_pause_then_quit(monkeypatch):
    frames = drive(
        [pygame.K_ESCAPE, pygame.K_ESCAPE, pygame.K_ESCAPE, pygame.K_q], monkeypatch
    )

    game.game_loop()

    assert pygame.display.get_init() is False
    assert frames["n"] >= 35


def test_q_does_nothing_until_paused(monkeypatch):
    frames = drive([pygame.K_q, pygame.K_ESCAPE, pygame.K_q], monkeypatch)

    game.game_loop()

    assert pygame.display.get_init() is False
    assert frames["n"] >= 30


def test_the_world_stops_while_paused(monkeypatch):
    ticks = []
    real = game.Human.update_anim

    def counting(self, kind):
        ticks.append(kind)
        return real(self, kind)

    monkeypatch.setattr(game.Human, "update_anim", counting)
    frames = drive([pygame.K_ESCAPE, None, None, None, pygame.K_q], monkeypatch)

    game.game_loop()

    assert len(ticks) < frames["n"]


def test_overlay_dims_the_frame(display, window):
    from shooter.ui import pause

    snapshot = pygame.Surface(window)
    snapshot.fill((255, 255, 255))

    pause.draw(display, window, snapshot)

    assert display.get_at((5, 5)).r < 255


def test_overlay_keeps_the_frame_underneath(display, window):
    from shooter.ui import pause

    snapshot = pygame.Surface(window)
    snapshot.fill((0, 200, 0))

    pause.draw(display, window, snapshot)

    corner = display.get_at((5, 5))
    assert corner.g > corner.r and corner.g > corner.b


def test_a_runaway_loop_is_caught_not_hung(monkeypatch):
    drive([], monkeypatch)

    with pytest.raises(LoopRanAwayError):
        game.game_loop()
