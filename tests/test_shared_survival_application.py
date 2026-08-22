"""The MatchHost-backed START GAME route uses neutral Survival runtime."""

import pygame

from shooter import config, game
from shooter.application import MatchHost
from shooter.commands import ControlFrame
from shooter.gameplay import GameplayScene, SurvivalGameplayScene
from shooter.settings import Settings
from shooter.scenes import SceneStack
from shooter.ui import menu, title
from shooter.viewport import Viewport

WINDOW = (1080, 720)


def test_production_start_route_opens_visible_shared_survival(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    host = MatchHost()
    stack.push(title.MainMenuScene(window, stack.manager))

    game.route(title.START, stack, window, Settings(), match_host=host)
    scene = stack.top

    assert isinstance(scene, SurvivalGameplayScene)
    assert scene.mode.player_id is not None
    assert len(scene.mode.enemy_ids) == config.WAVE_BASE
    scene.draw(pygame.Surface(WINDOW), 0.0)


def test_shared_survival_moves_kills_and_returns_to_menu(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    host = MatchHost()
    stack.push(title.MainMenuScene(window, stack.manager))
    game.route(title.START, stack, window, Settings(), match_host=host)
    scene = stack.top
    player = scene.mode.player_id
    first_enemy = scene.mode.enemy_ids[0]
    before = scene.match.spatial.get(player).transform

    scene.update(ControlFrame((1, 0)), config.SIM_DT)
    for _ in range(3):
        scene.handle(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
        )

    assert scene.match.spatial.get(player).transform.x > before.x
    assert scene.match.snapshot().entity(first_enemy).vitality.alive is False
    assert scene.match.mode_status.enemies_remaining == config.WAVE_BASE - 1

    game.route(game.PAUSE, stack, window, Settings(), match_host=host)
    game.route(menu.END_GAME, stack, window, Settings(), match_host=host)
    assert isinstance(stack.top, title.MainMenuScene)
    assert host.active_match is None


def test_direct_legacy_start_remains_only_as_a_temporary_test_harness(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    stack.push(title.MainMenuScene(window, stack.manager))

    game.route(title.START, stack, window, Settings())

    assert isinstance(stack.top, GameplayScene)
