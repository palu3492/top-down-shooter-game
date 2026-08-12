import contextlib
import math

import pygame

from shooter import config
from shooter.assets import asset_path, load_image
from shooter.background import BackgroundSheet
from shooter.entities.player import Human
from shooter.entities import powerups as powerup_kinds
from shooter.entities.powerups import PowerUps
from shooter.entities.projectiles import (
    BULLET_DAMAGE,
    LETHAL,
    Grenade,
    Shot,
    StunGrenade,
)
from shooter.systems.waves import WaveSystem
from shooter.render import blit_group
from shooter.ui import dev, menu
from shooter.ui.screens import ScreenStack
from shooter.ui.hud import HUD, Cash, GrenadeData, GunData, HealthBar
from shooter.ui.radar import RadarScreen

INSTAKILL_SECONDS = config.INSTAKILL_SECONDS


def collect_powerup(kind, human, zombie_group, gun):
    """Apply a collected power-up. Returns instakill seconds to add, if any."""
    if kind == powerup_kinds.NUKE:
        zombie_group.empty()
    elif kind == powerup_kinds.MAX_HEALTH:
        human.restore_health()
    elif kind == powerup_kinds.MAX_AMMO:
        gun.refill()
    elif kind == powerup_kinds.INSTAKILL:
        return INSTAKILL_SECONDS
    return 0.0


def reset_zombie_pos(zombie):
    zombie.reset_position()


def is_zombie_attacking(human, zombie, dt=config.SIM_DT):
    if pygame.sprite.collide_rect(human, zombie):
        zombie.update_anim("ATTACK", dt)
        if human.remove_health(config.ZOMBIE_DAMAGE * dt):
            zombie.update_anim("IDLE", dt)
            human.kill()


def explosion_touching_zombie(zombie, explosion):
    if pygame.sprite.collide_rect(zombie, explosion) and zombie.remove_health(
        config.EXPLOSION_DAMAGE
    ):
        zombie.kill()


def stun_explosion_touching_zombie(zombie, explosion):
    if pygame.sprite.collide_rect(zombie, explosion):
        zombie.remove_speed(config.STUN_SPEED)


def game_loop():
    pygame.init()
    window = config.WINDOW
    # SCALED keeps the render surface at WINDOW whatever size the window is, and
    # letterboxes to preserve aspect. Without it, going fullscreen changes the
    # surface itself and every fixed HUD offset moves with it.
    screen = pygame.display.set_mode(
        window, pygame.SCALED | pygame.RESIZABLE, vsync=config.VSYNC
    )
    screen.blit(
        pygame.font.Font(None, 40).render("Loading...", True, config.WHITE),
        (100, 100),
    )
    pygame.display.update()
    game_is_running = True
    screens = ScreenStack(window)
    frozen_frame = None
    pause_requested = False
    instakill_seconds = 0.0

    cursor = load_image("cursor.png")
    pygame.mouse.set_visible(False)

    camera_x, camera_y = 0, 0
    min_camera_x = -(config.WORLD[0] - window[0])
    min_camera_y = -(config.WORLD[1] - window[1])

    bck = BackgroundSheet(asset_path("Backgrounds/background_0.jpg"))

    heads_up_display = HUD(window)
    human = Human(window)
    radar = RadarScreen()
    player_cash = Cash()
    health_data = HealthBar(window)
    bullets = pygame.sprite.Group()
    grenades = pygame.sprite.Group()
    explosions = pygame.sprite.Group()
    stun_grenades = pygame.sprite.Group()
    stun_explosions = pygame.sprite.Group()
    all_grenade_data = GrenadeData()
    human_group = pygame.sprite.Group(human)
    zombie_group = pygame.sprite.Group()
    powerups_group = pygame.sprite.Group()
    powerups_group.add(PowerUps())

    wave_system = WaveSystem(window, zombie_group, player_cash)

    mouse_x = pygame.mouse.get_pos()[0]
    mouse_y = pygame.mouse.get_pos()[1]
    center_x = int(mouse_x - (window[0] / 2.0))
    center_y = -int(mouse_y - (window[1] / 2.0))

    ammo_class = GunData(window)
    ammo_count = ""

    clock = pygame.time.Clock()
    accumulator = 0.0
    change_x = change_y = 0
    shooting = False
    previous_camera = (camera_x, camera_y)
    while game_is_running:
        pressed = pygame.key.get_pressed()

        # When button is lifted up sets camera x,y change to 0
        if change_x <= 0 or change_y <= 0:
            human_anim = "IDLE"

        for event in pygame.event.get():
            if screens:
                if event.type == pygame.QUIT:
                    game_is_running = False
                    continue
                action = screens.handle(event)
                if action == menu.RESUME:
                    screens.clear()
                elif action == menu.SETTINGS:
                    screens.push(menu.SettingsScreen(window, screens.manager))
                elif action == menu.DEV:
                    screens.push(dev.DevScreen(window, screens.manager))
                elif action == menu.BACK:
                    screens.pop()
                elif action == menu.QUIT:
                    game_is_running = False
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and ammo_count not in (
                "no ammo",
                "reload",
            ):
                shooting = True
                bullet = Shot(
                    (window[0] / 2.0) - camera_x,
                    (window[1] / 2.0) - camera_y,
                    center_x,
                    center_y,
                    damage=LETHAL if instakill_seconds > 0 else BULLET_DAMAGE,
                )
                bullets.add(bullet)
                ammo_count = ammo_class.shooting_bullet()
            if event.type == pygame.QUIT:
                game_is_running = False
            if event.type == pygame.WINDOWRESIZED:
                # SCALED handles the scaling itself; re-reading the surface keeps
                # our reference valid if pygame swapped it out underneath us.
                screen = pygame.display.get_surface()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and not screens:
                    pause_requested = True
                if event.key == pygame.K_BACKSLASH:
                    # With SCALED this keeps the render surface intact; the old
                    # set_mode(FULLSCREEN) re-opened the window at 1080x720.
                    # Not every driver supports it -- SDL's dummy raises -- and a
                    # keypress must not be able to bring the game down.
                    with contextlib.suppress(pygame.error):
                        pygame.display.toggle_fullscreen()
                    screen = pygame.display.get_surface()
                if event.key == pygame.K_g and all_grenade_data.grenade_amount > 0:
                    grenade = Grenade(
                        (window[0] / 2.0) - camera_x,
                        (window[1] / 2.0) - camera_y,
                        center_x,
                        center_y,
                    )
                    grenades.add(grenade)
                    all_grenade_data.grenade_amount -= 1
                if event.key == pygame.K_f and all_grenade_data.stun_grenade_amount > 0:
                    stun_grenade = StunGrenade(
                        (window[0] / 2.0) - camera_x,
                        (window[1] / 2.0) - camera_y,
                        center_x,
                        center_y,
                    )
                    stun_grenades.add(stun_grenade)
                    all_grenade_data.stun_grenade_amount -= 1
                if event.key == pygame.K_r:
                    ammo_count = ammo_class.manual_reload()

        if screens:
            screens.draw(screen, frozen_frame, 1 / config.SIM_HZ)
            pygame.display.flip()
            clock.tick(config.FPS)
            accumulator = 0.0
            continue

        # Aim is sampled once per frame; the pointer does not move between steps.
        mouse_x, mouse_y = pygame.mouse.get_pos()
        center_x = int(mouse_x - (window[0] / 2))
        center_y = -int(mouse_y - (window[1] / 2))

        # ------------------------------------------------------------------
        # Simulation: fixed steps, however long the frame took to draw.
        # ------------------------------------------------------------------
        while accumulator >= config.SIM_DT:
            accumulator -= config.SIM_DT

            if human.alive():
                if pressed[pygame.K_w]:
                    change_y = config.PLAYER_SPEED * config.SIM_DT
                elif pressed[pygame.K_s]:
                    change_y = -config.PLAYER_SPEED * config.SIM_DT
                if pressed[pygame.K_a]:
                    change_x = config.PLAYER_SPEED * config.SIM_DT
                elif pressed[pygame.K_d]:
                    change_x = -config.PLAYER_SPEED * config.SIM_DT

            previous_camera = (camera_x, camera_y)
            camera_x = min(0, max(min_camera_x, camera_x + change_x))
            camera_y = min(0, max(min_camera_y, camera_y + change_y))

            if ammo_count == "reload":
                ammo_count = ammo_class.reloading(config.SIM_DT)

            # Preserves the original rule, quirks included: MOVE only when both
            # axes are positive, otherwise IDLE, and SHOOT overrides either.
            human_anim = "MOVE"
            if change_x <= 0 or change_y <= 0:
                human_anim = "IDLE"
            if shooting:
                human_anim = "SHOOT"
            human.update_anim(human_anim, config.SIM_DT)
            # Rotation resizes human.rect, which collision reads, so it has to
            # happen exactly once per step -- in the render pass it compounded
            # with frame rate and inflated the hitbox.
            human.rot_center(math.degrees(math.atan2(center_y, center_x)))

            for zombie in zombie_group:
                zombie.update_anim("MOVE", config.SIM_DT)
                is_zombie_attacking(human, zombie, config.SIM_DT)
                zombie.move_toward_center(camera_x, camera_y, config.SIM_DT)
                for explosion in explosions:
                    explosion_touching_zombie(zombie, explosion)
                for stun_explosion in stun_explosions:
                    stun_explosion_touching_zombie(zombie, stun_explosion)
                zombie.zombie_speed_timer(config.SIM_DT)

            for powerup in powerups_group:
                collected = powerup.update(human, camera_x, camera_y, config.SIM_DT)
                if collected is None:
                    continue
                if collected != powerup_kinds.EXPIRED:
                    instakill_seconds += collect_powerup(
                        collected, human, zombie_group, ammo_class
                    )
                powerup.kill()

            bullets.update(camera_x, camera_y, zombie_group, config.SIM_DT)
            grenades.update(camera_x, camera_y, explosions, config.SIM_DT)
            explosions.update(camera_x, camera_y, config.SIM_DT)
            stun_grenades.update(camera_x, camera_y, stun_explosions, config.SIM_DT)
            stun_explosions.update(camera_x, camera_y, config.SIM_DT)

            if len(zombie_group) == 0:
                wave_system.advance(window, zombie_group, player_cash, config.SIM_DT)

            if instakill_seconds > 0:
                instakill_seconds = max(0.0, instakill_seconds - config.SIM_DT)

            change_x = change_y = 0
            shooting = False

        # ------------------------------------------------------------------
        # Render: once per frame, at whatever rate the machine manages.
        # ------------------------------------------------------------------
        alpha = accumulator / config.SIM_DT
        draw_x = previous_camera[0] + (camera_x - previous_camera[0]) * alpha
        draw_y = previous_camera[1] + (camera_y - previous_camera[1]) * alpha

        image = bck.image_at((0 - draw_x, 0 - draw_y, window[0], window[1]))
        screen.blit(image, (0, 0))

        blit_group(screen, powerups_group, draw_x, draw_y, alpha)
        for zombie in zombie_group:
            zombie.health_bar(screen, zombie.draw_position(draw_x, draw_y, alpha))
        blit_group(screen, zombie_group, draw_x, draw_y, alpha)
        human_group.draw(screen)
        blit_group(screen, bullets, draw_x, draw_y, alpha)

        if len(zombie_group) == 0:
            wave_system.draw(screen)

        blit_group(screen, grenades, draw_x, draw_y, alpha)
        blit_group(screen, explosions, draw_x, draw_y, alpha)
        blit_group(screen, stun_grenades, draw_x, draw_y, alpha)
        blit_group(screen, stun_explosions, draw_x, draw_y, alpha)

        radar.draw(screen, -camera_x + window[0] / 2, -camera_y + window[1] / 2)
        for zombie in zombie_group:
            radar.update_zom(screen, zombie)

        if instakill_seconds > 0:
            screen.blit(
                pygame.font.Font(None, 34).render(
                    f"INSTAKILL {int(instakill_seconds) + 1}s",
                    True,
                    config.INSTAKILL_TEXT,
                ),
                (window[0] / 2.0 - 70, 40),
            )

        heads_up_display.update(screen, window)
        health_data.draw(screen, human.get_health())
        ammo_class.update(screen)
        player_cash.update(screen)

        if ammo_count == "reload":
            screen.blit(
                pygame.font.Font(None, 30).render("Reloading", True, config.WHITE),
                ((window[0] / 2.0) - 50, 100),
            )

        screen.blit(
            pygame.font.Font(None, 20).render(str(clock.get_fps()), True, config.WHITE),
            (0, 0),
        )

        if pause_requested:
            frozen_frame = screen.copy()
            screens.push(menu.PauseScreen(window, screens.manager))
            pause_requested = False

        screen.blit(cursor, (mouse_x - 23, mouse_y - 22))
        pygame.display.flip()
        accumulator += min(clock.tick(config.FPS) / 1000.0, config.MAX_FRAME_SECONDS)

    pygame.quit()
