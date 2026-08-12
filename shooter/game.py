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
from shooter.ui import pause
from shooter.ui.hud import HUD, Cash, GrenadeData, GunData, HealthBar
from shooter.ui.radar import RadarScreen

PLAYING, PAUSED = "PLAYING", "PAUSED"

INSTAKILL_FRAMES = config.INSTAKILL_FRAMES


def collect_powerup(kind, human, zombie_group, gun):
    """Apply a collected power-up. Returns instakill frames to add, if any."""
    if kind == powerup_kinds.NUKE:
        zombie_group.empty()
    elif kind == powerup_kinds.MAX_HEALTH:
        human.restore_health()
    elif kind == powerup_kinds.MAX_AMMO:
        gun.refill()
    elif kind == powerup_kinds.INSTAKILL:
        return INSTAKILL_FRAMES
    return 0


def reset_zombie_pos(zombie):
    zombie.reset_position()


def is_zombie_attacking(human, zombie):
    if pygame.sprite.collide_rect(human, zombie):
        zombie.update_anim("ATTACK")
        if human.remove_health(
            config.ZOMBIE_DAMAGE
        ):  # if return True (player is dead) then change to idle and kill player
            zombie.update_anim("IDLE")
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
    screen = pygame.display.set_mode(window)
    screen.blit(
        pygame.font.Font(None, 40).render("Loading...", True, config.WHITE),
        (100, 100),
    )
    pygame.display.update()
    game_is_running = True
    fullscreen_flag = True
    state = PLAYING
    paused_frame = None
    instakill_frames = 0

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
    while game_is_running:
        change_x = change_y = 0
        human_anim = "MOVE"

        pressed = pygame.key.get_pressed()

        # Controls for moving the camera, moving 40 px per frame
        if state == PLAYING and human.alive():
            if pressed[pygame.K_w]:
                change_y = config.PLAYER_SPEED
            elif pressed[pygame.K_s]:
                change_y = -config.PLAYER_SPEED
            if pressed[pygame.K_a]:
                change_x = config.PLAYER_SPEED
            elif pressed[pygame.K_d]:
                change_x = -config.PLAYER_SPEED

        camera_x += change_x
        camera_y += change_y

        if camera_x > 0:
            camera_x = 0
        elif camera_x < min_camera_x:
            camera_x = min_camera_x
        if camera_y > 0:
            camera_y = 0
        elif camera_y < min_camera_y:
            camera_y = min_camera_y

        # When button is lifted up sets camera x,y change to 0
        if change_x <= 0 or change_y <= 0:
            human_anim = "IDLE"

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and ammo_count not in (
                "no ammo",
                "reload",
            ):
                human_anim = "SHOOT"
                bullet = Shot(
                    (window[0] / 2.0) - camera_x,
                    (window[1] / 2.0) - camera_y,
                    center_x,
                    center_y,
                    damage=LETHAL if instakill_frames else BULLET_DAMAGE,
                )
                bullets.add(bullet)
                ammo_count = ammo_class.shooting_bullet()
            if event.type == pygame.QUIT:
                game_is_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == PLAYING:
                        state = PAUSED
                        paused_frame = screen.copy()
                    else:
                        state = PLAYING
                if event.key == pygame.K_q and state == PAUSED:
                    game_is_running = False
                if event.key == pygame.K_BACKSLASH:
                    fullscreen_flag = not fullscreen_flag
                    screen = pygame.display.set_mode(
                        window, pygame.FULLSCREEN if fullscreen_flag else 0
                    )
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

        if state == PAUSED:
            pause.draw(screen, window, paused_frame)
            pygame.display.flip()
            clock.tick(config.FPS)
            continue

        if ammo_count == "reload":
            ammo_count = ammo_class.reloading()

        # Human
        if human_anim == "IDLE":
            human.update_anim("IDLE")
        elif human_anim == "MOVE":
            human.update_anim("MOVE")
        elif human_anim == "SHOOT":
            human.update_anim("SHOOT")

        # Controls background rendering
        image = bck.image_at((0 - camera_x, 0 - camera_y, window[0], window[1]))
        screen.blit(image, (0, 0))

        # 1. Updates zombie animation
        # 1. Checks if Zombie is attacking
        # 2. Sends zombie to Human
        # 3. Moves Zombies when camera moves
        for zombie in zombie_group:
            zombie.update_anim("MOVE")
            is_zombie_attacking(human, zombie)
            zombie.move_toward_center(camera_x, camera_y)
            zombie.health_bar(screen)
            for explosion in explosions:
                explosion_touching_zombie(zombie, explosion)
            for stun_explosion in stun_explosions:
                stun_explosion_touching_zombie(zombie, stun_explosion)
            zombie.zombie_speed_timer()  # count down any active stun

        # Mouse Controls
        mouse_x = pygame.mouse.get_pos()[0]
        mouse_y = pygame.mouse.get_pos()[1]
        center_x = int(mouse_x - (window[0] / 2))
        center_y = -int(mouse_y - (window[1] / 2))
        rotation_angle = math.degrees(math.atan2(center_y, center_x))
        human.rot_center(rotation_angle)

        ###################################
        #
        #           Updates PowerUps
        #           Draws to screen
        #
        ###################################
        for powerup in powerups_group:
            collected = powerup.update(human, change_x, change_y)
            if collected is None:
                continue
            if collected != powerup_kinds.EXPIRED:
                instakill_frames += collect_powerup(
                    collected, human, zombie_group, ammo_class
                )
            powerup.kill()
        powerups_group.draw(screen)

        # Loads in Human and Zombie
        zombie_group.draw(screen)
        human_group.draw(screen)

        # Bullet animation
        bullets.update(camera_x, camera_y, zombie_group)
        bullets.draw(screen)

        if len(zombie_group) == 0 and wave_system.wave_gui(screen):
            wave_system.wave_control(screen, window, zombie_group, player_cash)

        # Grenades and explosions
        grenades.update(camera_x, camera_y, screen, explosions)
        grenades.draw(screen)
        explosions.update(camera_x, camera_y)
        explosions.draw(screen)
        stun_grenades.update(camera_x, camera_y, screen, stun_explosions)
        stun_grenades.draw(screen)
        stun_explosions.update(camera_x, camera_y)
        stun_explosions.draw(screen)

        # Draw crosshair cursor
        screen.blit(cursor, (mouse_x - 23, mouse_y - 22))

        # Updating radar with new data, Human and Zombies
        radar.draw(screen, -camera_x + window[0] / 2, -camera_y + window[1] / 2)
        for zombie in zombie_group:
            radar.update_zom(screen, zombie)

        if instakill_frames:
            instakill_frames -= 1
            seconds = instakill_frames // config.FPS + 1
            screen.blit(
                pygame.font.Font(None, 34).render(
                    f"INSTAKILL {seconds}s", True, config.INSTAKILL_TEXT
                ),
                (window[0] / 2.0 - 70, 40),
            )

        heads_up_display.update(screen, window)
        # Updates Health Bar
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
        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()
