"""The application shell: a window, a clock, and whatever scene is on top.

What is left here is everything that outlives any one scene -- the display, the
fixed timestep, the event pump, the settings, and the crosshair and frame
counter that belong to the application rather than to the world.
"""

import contextlib
from collections import namedtuple

import pygame

from shooter import config
from shooter.assets import load_image
from shooter.gameplay import PAUSE, GameplayScene
from shooter.preload import preload
from shooter.scenes import SceneStack
from shooter.settings import Settings
from shooter.ui import dev, menu, settings_screen
from shooter.ui.layout import LayoutOverflowError
from shooter.viewport import Viewport

LOADING_AT = (100, 100)
CURSOR_OFFSET = pygame.Vector2(-23, -22)
FPS_READOUT = (0, 0)

Inputs = namedtuple("Inputs", "pressed pointer")


def open_display(window):
    """SCALED keeps the render surface at `window` whatever size the OS window
    is, and letterboxes to preserve aspect.

    Deliberately without RESIZABLE. Calling `set_mode` a second time with
    SCALED and RESIZABLE together aborts inside SDL -- reproducibly on Linux,
    intermittently on macOS -- and AT25 made that second call a thing players
    can trigger from the settings screen. SCALED on its own survives repeated
    changes, and the window size is a setting now rather than something to drag.
    """
    return pygame.display.set_mode(tuple(window), pygame.SCALED, vsync=config.VSYNC)


def match_resolution(window, scenes):
    """Rebuild the display when the setting no longer matches what is on screen.

    Nothing here touches the world. Positions are in world coordinates and
    health is a number, so a resolution change cannot invalidate any of it --
    only the surface and the layout are made again.
    """
    if window == config.WINDOW:
        return None
    window.resize(config.WINDOW)
    surface = open_display(window)
    scenes.resize(window)
    for scene in scenes.visible():
        if scene.simulates:
            scene.session.resize()
    return surface


def open_scene(scenes, scene):
    """A scene too big for the window must not end the game -- the menu the
    player is already looking at stays open instead."""
    with contextlib.suppress(LayoutOverflowError):
        scenes.push(scene)


def show_loading(screen):
    screen.blit(
        pygame.font.Font(None, 40).render("Loading...", True, config.WHITE),
        LOADING_AT,
    )
    pygame.display.update()


def route(action, scenes, window, settings):
    """Turn a scene's action into a move on the stack. False means quit."""
    if action == PAUSE:
        open_scene(scenes, menu.PauseScreen(window, scenes.manager))
    elif action in (menu.RESUME, menu.BACK):
        scenes.pop()
    elif action == menu.SETTINGS:
        open_scene(
            scenes, settings_screen.SettingsScreen(window, scenes.manager, settings)
        )
    elif action == menu.DEV:
        open_scene(scenes, dev.DevScreen(window, scenes.manager, settings))
    elif action == menu.QUIT:
        return False
    return True


def game_loop():
    pygame.init()
    settings = Settings()
    settings.load()
    settings.apply_at_startup()

    window = Viewport(config.WINDOW)
    screen = open_display(window)
    show_loading(screen)
    preload()

    cursor = load_image("cursor.png")
    scenes = SceneStack(window)
    scenes.push(GameplayScene(window, scenes.manager))

    clock = pygame.time.Clock()
    accumulator = 0.0
    running = True

    while running:
        screen = match_resolution(window, scenes) or screen
        pointer = pygame.mouse.get_pos()
        inputs = Inputs(pygame.key.get_pressed(), pointer)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSLASH:
                # With SCALED this keeps the render surface intact; the old
                # set_mode(FULLSCREEN) re-opened the window at 1080x720. Not
                # every driver supports it -- SDL's dummy raises -- and a
                # keypress must not be able to bring the game down.
                with contextlib.suppress(pygame.error):
                    pygame.display.toggle_fullscreen()
                screen = pygame.display.get_surface()
                continue
            running = route(scenes.handle(event), scenes, window, settings)
            if not running:
                break

        if scenes.simulates:
            while accumulator >= config.SIM_DT:
                accumulator -= config.SIM_DT
                scenes.update(inputs, config.SIM_DT)
        else:
            # Time must not bank while a menu is up, or resuming would apply
            # the whole pause in a single step.
            accumulator = 0.0

        scenes.draw(screen, accumulator / config.SIM_DT, 1 / config.SIM_HZ)

        if scenes.simulates:
            screen.blit(cursor, pygame.Vector2(pointer) + CURSOR_OFFSET)
        screen.blit(
            pygame.font.Font(None, 20).render(str(clock.get_fps()), True, config.WHITE),
            FPS_READOUT,
        )
        pygame.display.flip()
        accumulator += min(clock.tick(config.FPS) / 1000.0, config.MAX_FRAME_SECONDS)

    pygame.quit()
