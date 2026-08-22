"""Integration checkpoint 3: Sandbox is visible and switchable in-app."""

from dataclasses import replace

import pygame

from shooter import config, game
from shooter.application import MatchHost
from shooter.commands import ControlFrame
from shooter.gameplay import GameplayScene, SandboxGameplayScene
from shooter.map_definition import current_map_definition
from shooter.match import DISPOSED
from shooter.match_configuration import (
    SANDBOX,
    ZOMBIE_SURVIVAL,
    MapCatalog,
    MatchConfiguration,
    default_mode_catalog,
)
from shooter.scenes import Scene, SceneStack
from shooter.settings import Settings
from shooter.systems import levels
from shooter.ui import menu, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)


class SelectionRoot(Scene):
    def open(self):
        pass


def test_main_menu_exposes_a_visible_sandbox_route(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    host = MatchHost()
    stack.push(title.MainMenuScene(window, stack.manager))

    assert title.SANDBOX in [action for _, action in stack.top.entries]

    game.route(title.SANDBOX, stack, window, Settings(), match_host=host)

    assert isinstance(stack.top, SandboxGameplayScene)
    assert stack.top.match.configuration.mode_id == SANDBOX
    assert set(stack.top.mode.actor_ids) == {"red", "blue"}


def test_visible_sandbox_moves_attacks_draws_and_returns_to_menu(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    host = MatchHost()
    stack.push(title.MainMenuScene(window, stack.manager))
    game.start_sandbox(stack, window, match_host=host)
    scene = stack.top
    red = scene.mode.actor_ids["red"]
    blue = scene.mode.actor_ids["blue"]
    before_x = scene.match.spatial.get(red).transform.x

    scene.update(ControlFrame((1, 0)), config.SIM_DT)
    scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
    scene.draw(pygame.Surface(WINDOW), 0.0)

    assert scene.match.spatial.get(red).transform.x > before_x
    assert scene.match.combat.get(blue).health == 90

    game.route(game.PAUSE, stack, window, Settings(), match_host=host)
    game.route(menu.END_GAME, stack, window, Settings(), match_host=host)

    assert isinstance(stack.top, title.MainMenuScene)
    assert host.active_match is None


def test_switching_map_and_mode_disposes_old_match_and_starts_fresh(display):
    original = current_map_definition()
    alternate = replace(original, map_id="alternate_arena", display_name="Alternate")
    host = MatchHost(
        default_mode_catalog(),
        MapCatalog((original, alternate)),
        MatchConfiguration(SANDBOX, alternate.map_id, 77),
    )
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    stack.push(SelectionRoot(window, stack.manager))

    game.start_sandbox(stack, window, match_host=host)
    sandbox_match = host.active_match
    sandbox_match.advance(1.0)
    assert sandbox_match.configuration.map_id == alternate.map_id

    stack.pop()
    host.select(MatchConfiguration(ZOMBIE_SURVIVAL, original.map_id, 88))
    game.start_level(stack, window, levels.FIRST, match_host=host)
    survival_match = host.active_match

    assert sandbox_match.state == DISPOSED
    assert isinstance(stack.top, GameplayScene)
    assert survival_match is not sandbox_match
    assert survival_match.configuration.mode_id == ZOMBIE_SURVIVAL
    assert survival_match.configuration.map_id == original.map_id
    assert survival_match.tick == 0
