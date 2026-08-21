import itertools
import os

import pygame

from shooter.assets import ASSETS_DIR
from shooter.entities import player, zombie

MODULES = [
    "shooter.assets",
    "shooter.background",
    "shooter.game",
    "shooter.entities.player",
    "shooter.entities.zombie",
    "shooter.entities.projectiles",
    "shooter.entities.powerups",
    "shooter.ui.hud",
    "shooter.ui.radar",
    "shooter.systems.waves",
]


def test_every_module_imports():
    for name in MODULES:
        __import__(name)


def test_every_animation_frame_resolves_case_sensitively():
    # Exact set membership, not os.path.exists -- the latter is case-insensitive
    # on macOS and would pass even with the pre-AT3 uppercase paths restored.
    on_disk = {
        os.path.join(root, name)
        for root, _, files in os.walk(ASSETS_DIR)
        for name in files
    }

    missing = [
        os.path.join(ASSETS_DIR, directory, f"{prefix}{i}.png")
        for directory, prefix, count in zombie.ANIMATIONS.values()
        for i in range(count)
        if os.path.join(ASSETS_DIR, directory, f"{prefix}{i}.png") not in on_disk
    ]

    if os.path.join(ASSETS_DIR, player.PLAYER_IMAGE) not in on_disk:
        missing.append(os.path.join(ASSETS_DIR, player.PLAYER_IMAGE))

    assert missing == []


def test_assets_resolve_independently_of_the_working_directory():
    assert ASSETS_DIR.is_absolute()
    assert ASSETS_DIR.is_dir()


def test_game_loop_runs_600_frames_then_exits_cleanly(monkeypatch):
    frames = itertools.count(1)
    real_flip = pygame.display.flip

    def flip():
        if next(frames) >= 600:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)

    from shooter.game import game_loop

    game_loop()

    assert pygame.display.get_init() is False
