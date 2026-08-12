"""The application shell: a window, a clock, and whatever is running inside it.

What is left here is everything that outlives a game -- the display, the fixed
timestep, the event pump, the settings and the menus. The world itself lives in
`Session`, so it can be built and thrown away without touching any of this.
"""

import contextlib

import pygame

from shooter import config
from shooter.assets import load_image
from shooter.session import Session
from shooter.settings import Settings
from shooter.ui import dev, menu, settings_screen
from shooter.ui.layout import LayoutOverflowError
from shooter.ui.screens import ScreenStack
from shooter.viewport import Viewport

LOADING_AT = (100, 100)
CURSOR_OFFSET = (-23, -22)


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


def match_resolution(window, screens, session):
    """Rebuild the display when the setting no longer matches what is on screen.

    Nothing here touches the world. Positions are in world coordinates and
    health is a number, so a resolution change cannot invalidate any of it --
    only the surface and the layout are made again.
    """
    if window == config.WINDOW:
        return None
    window.resize(config.WINDOW)
    surface = open_display(window)
    screens.resize(window)
    session.resize(window)
    return surface


def open_screen(screens, screen):
    """A screen too big for the window must not end the game -- the menu the
    player is already looking at stays open instead."""
    with contextlib.suppress(LayoutOverflowError):
        screens.push(screen)


def show_loading(screen):
    screen.blit(
        pygame.font.Font(None, 40).render("Loading...", True, config.WHITE),
        LOADING_AT,
    )
    pygame.display.update()


def game_loop():
    pygame.init()
    settings = Settings()
    settings.load()
    settings.apply_at_startup()

    window = Viewport(config.WINDOW)
    screen = open_display(window)
    show_loading(screen)

    screens = ScreenStack(window)
    cursor = load_image("cursor.png")
    pygame.mouse.set_visible(False)

    session = Session(window)
    clock = pygame.time.Clock()
    accumulator = 0.0
    frozen_frame = None
    pause_requested = False
    running = True

    while running:
        screen = match_resolution(window, screens, session) or screen
        pressed = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if screens:
                action = screens.handle(event)
                if action == menu.RESUME:
                    screens.clear()
                elif action == menu.SETTINGS:
                    open_screen(
                        screens,
                        settings_screen.SettingsScreen(
                            window, screens.manager, settings
                        ),
                    )
                elif action == menu.DEV:
                    open_screen(
                        screens, dev.DevScreen(window, screens.manager, settings)
                    )
                elif action == menu.BACK:
                    screens.pop()
                elif action == menu.QUIT:
                    running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pause_requested = True
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSLASH:
                # With SCALED this keeps the render surface intact; the old
                # set_mode(FULLSCREEN) re-opened the window at 1080x720. Not
                # every driver supports it -- SDL's dummy raises -- and a
                # keypress must not be able to bring the game down.
                with contextlib.suppress(pygame.error):
                    pygame.display.toggle_fullscreen()
                screen = pygame.display.get_surface()
                continue
            session.handle(event)

        if screens:
            screens.draw(screen, frozen_frame, 1 / config.SIM_HZ)
            pygame.display.flip()
            clock.tick(config.FPS)
            accumulator = 0.0
            continue

        pointer = pygame.mouse.get_pos()
        session.aim_at(pointer)

        while accumulator >= config.SIM_DT:
            accumulator -= config.SIM_DT
            session.step(pressed, config.SIM_DT)

        session.draw(screen, accumulator / config.SIM_DT, fps=clock.get_fps())

        if pause_requested:
            # Captured beneath the crosshair, or the veiled backdrop keeps one
            # where the mouse used to be alongside the live pointer.
            frozen_frame = screen.copy()
            screens.push(menu.PauseScreen(window, screens.manager))
            pause_requested = False

        # the same sample the aim used, so the crosshair cannot draw a frame
        # away from where a bullet would actually go
        screen.blit(cursor, pygame.Vector2(pointer) + CURSOR_OFFSET)
        pygame.display.flip()
        accumulator += min(clock.tick(config.FPS) / 1000.0, config.MAX_FRAME_SECONDS)

    pygame.quit()
