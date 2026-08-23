"""The MatchHost-backed START GAME route uses neutral Survival runtime."""

import pygame

from shooter import config, game
from shooter.application import MatchHost
from shooter.commands import ControlFrame
from shooter.gameplay import GameplayScene, SurvivalGameplayScene
from shooter.match import DISPOSED
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
    scene.match.spatial.move_to(first_enemy, before.x + 800, before.y)
    for enemy_id in scene.mode.enemy_ids[1:]:
        scene.match.spatial.move_to(enemy_id, before.x, before.y + 400)

    scene.update(ControlFrame((1, 0)), config.SIM_DT)
    assert scene.camera[0] < window[0] / 2 - before.x
    for _ in range(5):
        target = scene.match.spatial.get(first_enemy).transform
        camera_x, camera_y = scene.camera
        scene.handle(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=(target.x + camera_x, target.y + camera_y),
            )
        )
        scene.update(ControlFrame(), 1 / 6)

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


def test_shared_survival_defeat_opens_result_and_retry_starts_fresh_match(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    host = MatchHost()
    stack.push(title.MainMenuScene(window, stack.manager))
    game.route(title.START, stack, window, Settings(), match_host=host)
    defeated_scene = stack.top
    defeated_match = defeated_scene.match
    defeated_match.combat.deplete(
        defeated_scene.mode.player_id, config.PLAYER_HEALTH
    )

    outcome = defeated_scene.tick(0.0)
    assert outcome == "LOST"
    assert defeated_scene.tick(0.0) is None
    game.route(outcome, stack, window, Settings(), match_host=host)

    assert isinstance(stack.top, menu.ResultScreen)
    assert stack.top.title == "YOU DIED"

    game.route(menu.RETRY, stack, window, Settings(), match_host=host)

    restarted = stack.top
    assert isinstance(restarted, SurvivalGameplayScene)
    assert restarted.match is host.active_match
    assert restarted.match is not defeated_match
    assert defeated_match.state == DISPOSED
    assert restarted.match.combat.get(restarted.mode.player_id).health == 100
    assert restarted.match.mode_status.wave == 1
    assert restarted.match.mode_status.cash == 0
