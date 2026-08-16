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
from shooter.progress import Progress
from shooter.scenes import SceneStack
from shooter import session
from shooter.settings import Settings
from shooter.systems import levels
from shooter.ui import dev, menu, settings_screen, title
from shooter.ui.layout import LayoutOverflowError
from shooter.viewport import Viewport

LOADING_AT = (100, 100)
CURSOR_OFFSET = pygame.Vector2(-23, -22)
FPS_READOUT = (0, 0)

# `trigger` is the left button *held*, which only an automatic weapon reads.
Inputs = namedtuple("Inputs", "pressed pointer trigger", defaults=(False,))


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


def played_level(scenes):
    """The level of the game currently on the stack, wherever it sits.

    A result screen is asked what to do next while the game that produced it is
    still underneath, which is where the answer is.
    """
    for scene in reversed(list(scenes.visible())):
        rules = getattr(getattr(scene, "session", None), "rules", None)
        if getattr(rules, "level", None) is not None:
            return rules.level
    return None


def start_level(scenes, window, level, replacing=0):
    """Put a game of this level on the stack, dropping whatever it replaces."""
    for _ in range(replacing):
        scenes.pop()
    open_scene(
        scenes,
        GameplayScene(window, scenes.manager, rules=levels.rules_for(level)),
    )


def remember(progress, level):
    """Note a finished level, and tolerate not being able to write it down.

    A read-only config directory or a full disk must not end the game at the
    moment the player has just won -- the same rule `open_scene` follows for a
    screen that will not fit, and the fullscreen toggle for a driver that
    refuses. The session keeps the progress either way; only the file is lost.
    """
    progress.record(level.number)
    with contextlib.suppress(OSError):
        progress.save()


def show_loading(screen):
    screen.blit(
        pygame.font.Font(None, 40).render("Loading...", True, config.WHITE),
        LOADING_AT,
    )
    pygame.display.update()


def route(action, scenes, window, settings, progress=None):
    """Turn a scene's action into a move on the stack. False means quit.

    Every navigation decision the game makes is here, which is the whole of
    what "start a game" and "end a game" turned out to be.
    """
    if action is None:
        return True
    if action == PAUSE:
        open_scene(scenes, menu.PauseScreen(window, scenes.manager))
    elif action == title.MENU:
        # The splash is replaced rather than covered: there is nothing to come
        # back to once the game has been introduced.
        scenes.pop()
        open_scene(scenes, title.MainMenuScene(window, scenes.manager, progress))
    elif action == title.START:
        start_level(scenes, window, levels.FIRST)
    elif action == title.CONTINUE:
        reached = progress.reached if progress else levels.FIRST.number
        start_level(scenes, window, levels.level_number(reached))
    elif action in (session.LOST, session.WON):
        level = played_level(scenes)
        if action == session.WON and level is not None and progress is not None:
            remember(progress, level)
        open_scene(
            scenes,
            menu.ResultScreen(
                window,
                scenes.manager,
                action,
                level,
                last=level is not None and level is levels.LEVELS[-1],
            ),
        )
    elif action == menu.RETRY:
        start_level(scenes, window, played_level(scenes) or levels.FIRST, replacing=2)
    elif action == menu.NEXT_LEVEL:
        finished = played_level(scenes) or levels.FIRST
        start_level(
            scenes, window, levels.level_number(finished.number + 1), replacing=2
        )
    elif action == menu.END_GAME:
        # The main menu is still underneath, so ending a game is dropping
        # whatever is over it and finding it where it was left.
        while len(scenes) > 1:
            scenes.pop()
    elif action in (menu.RESUME, menu.BACK):
        scenes.pop()
    elif action == menu.SETTINGS:
        open_scene(
            scenes, settings_screen.SettingsScreen(window, scenes.manager, settings)
        )
    elif action == menu.DEV:
        playing = next(
            (
                scene.session
                for scene in reversed(scenes.visible())
                if getattr(scene, "session", None) is not None
            ),
            None,
        )
        cash = playing.cash if playing is not None else None
        open_scene(scenes, dev.DevScreen(window, scenes.manager, settings, cash))
    elif action == menu.QUIT:
        return False
    return True


def game_loop():
    pygame.init()
    settings = Settings()
    settings.load()
    settings.apply_at_startup()

    progress = Progress(last_level=levels.LEVELS[-1].number)
    progress.load()

    window = Viewport(config.WINDOW)
    screen = open_display(window)
    show_loading(screen)
    preload()

    cursor = load_image("cursor.png")
    scenes = SceneStack(window)
    scenes.push(title.SplashScene(window, scenes.manager))

    clock = pygame.time.Clock()
    accumulator = 0.0
    frame_seconds = 0.0
    running = True

    while running:
        screen = match_resolution(window, scenes) or screen
        pointer = pygame.mouse.get_pos()
        inputs = Inputs(
            pygame.key.get_pressed(), pointer, pygame.mouse.get_pressed()[0]
        )

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
            running = route(scenes.handle(event), scenes, window, settings, progress)
            if not running:
                break

        running = (
            route(scenes.tick(frame_seconds), scenes, window, settings, progress)
            and running
        )

        if scenes.simulates:
            while accumulator >= config.SIM_DT:
                accumulator -= config.SIM_DT
                scenes.update(inputs, config.SIM_DT)
        else:
            # Time must not bank while a menu is up, or resuming would apply
            # the whole pause in a single step.
            accumulator = 0.0

        scenes.draw(screen, accumulator / config.SIM_DT)

        if scenes.simulates:
            screen.blit(cursor, pygame.Vector2(pointer) + CURSOR_OFFSET)
        screen.blit(
            pygame.font.Font(None, 20).render(str(clock.get_fps()), True, config.WHITE),
            FPS_READOUT,
        )
        pygame.display.flip()
        frame_seconds = min(clock.tick(config.FPS) / 1000.0, config.MAX_FRAME_SECONDS)
        accumulator += frame_seconds

        if not scenes:
            running = False

    pygame.quit()
