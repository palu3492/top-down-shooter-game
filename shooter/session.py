"""One playthrough: the world, and how it advances and draws.

`game_loop` used to hold all of this as fifty locals, which meant there was
nothing to construct and nothing to discard -- and so no way to start a game,
end one, or have none running while a menu is up.

The rules arrive as a collaborator. `WaveSystem` is the freeplay rules today;
a campaign replaces it without this file changing.

World state -- positions, health, cash, the wave count -- lives in plain
attributes that never hold a `Surface`, so writing a session to disk later is
additive rather than a rewrite.
"""

import math

import pygame

from shooter import config
from shooter.background import BackgroundSheet
from shooter.entities import powerups as powerup_kinds
from shooter.entities.player import Human
from shooter.entities.zombie import keep_apart
from shooter.entities.powerups import PowerUps
from shooter.entities.projectiles import (
    LETHAL,
    Grenade,
    Shot,
    StunGrenade,
)
from shooter.render import blit_group
from shooter.systems.waves import WaveSystem
from shooter.ui.hud import HUD, Cash, GrenadeData, GunPanel, HealthBar
from shooter.ui.radar import RadarScreen
from shooter.weapons import NO_AMMO, RELOAD, Gun
from shooter.viewport import visible_world

INSTAKILL_SECONDS = config.INSTAKILL_SECONDS
INSTAKILL_TOP = 40
RELOADING_TOP = 100
BACKGROUND = "Backgrounds/background_0.jpg"

# Firing is the left button only. Any `MOUSEBUTTONDOWN` used to do it, so a
# right-click, a middle-click or either side button emptied the clip -- and `E`
# being the interaction means the other buttons have their own jobs coming.
LEFT_BUTTON = 1

# How a game can finish. `None` means it is still being played.
LOST, WON = "LOST", "WON"


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


def centred_text(screen, window, message, top, size, colour=config.WHITE):
    """Measured and centred rather than nudged by a hand-tuned offset.

    `window[0] / 2 - 70` was only ever centred for one particular string at one
    particular font size.
    """
    text = pygame.font.Font(None, size).render(message, True, colour)
    screen.blit(text, (window[0] / 2.0 - text.get_width() / 2.0, top))


class Session:
    """A game in progress."""

    def __init__(self, window, rules=WaveSystem):
        self.window = window
        self.camera_x, self.camera_y = 0, 0
        self.previous_camera = (0, 0)
        self.instakill_seconds = 0.0
        # Sampled now rather than left at the origin: input is handled before
        # the loop first calls `aim_at`, so a click on the opening frame would
        # otherwise fire at atan2(0, 0) -- straight right, wherever the pointer.
        self.aim = (0, 0)
        self.aim_at(pygame.mouse.get_pos())

        self.change_x = self.change_y = 0
        self.shooting = False
        self.ammo_count = ""

        self.background = BackgroundSheet(BACKGROUND)
        self.human = Human(window)
        self.human_group = pygame.sprite.Group(self.human)
        self.zombies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.grenades = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.stun_grenades = pygame.sprite.Group()
        self.stun_explosions = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group(PowerUps())

        self.cash = Cash()
        self.gun = Gun()
        self.grenade_data = GrenadeData()
        self.heads_up_display = HUD(window)
        self.health_display = HealthBar(window)
        self.gun_display = GunPanel(window)
        self.radar = RadarScreen()

        self.rules = rules(window, self.zombies, self.cash, self.visible)

    @property
    def outcome(self):
        """`None` while the game is still being played.

        Losing belongs to the session: a player at zero health is lost whatever
        mode is being played. Winning belongs to the rules, because what counts
        as finished is exactly what a mode decides -- endless freeplay never
        declares one.
        """
        if not self.human.alive():
            return LOST
        return self.rules.outcome

    @property
    def visible(self):
        return visible_world((self.camera_x, self.camera_y), self.window)

    @property
    def camera(self):
        return (self.camera_x, self.camera_y)

    def resize(self):
        """Take no window: there is only ever one.

        AT25 replaced twenty copies of the render size with a single shared
        `Viewport`, so the gun, the health bar and every zombie already read the
        new size the moment it changes. Accepting a window here would imply
        there are copies to update and quietly leave most of them stale -- the
        player is the only thing holding a position derived from it.
        """
        self.human.recentre(self.window)

    def aim_at(self, pointer):
        """Sampled once per frame; the pointer does not move between steps."""
        self.aim = (
            int(pointer[0] - self.window[0] / 2),
            -int(pointer[1] - self.window[1] / 2),
        )

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT_BUTTON:
            self._shoot()
        elif event.type == pygame.KEYDOWN:
            self._key(event.key)

    def _shoot(self):
        if self.ammo_count in (NO_AMMO, RELOAD):
            return
        self.shooting = True
        self.bullets.add(
            Shot(
                *self._muzzle(),
                *self.aim,
                damage=LETHAL if self.instakill_seconds > 0 else self.gun.damage,
            )
        )
        self.ammo_count = self.gun.fire()

    def _key(self, key):
        if key == pygame.K_g and self.grenade_data.grenade_amount > 0:
            self.grenades.add(Grenade(*self._muzzle(), *self.aim))
            self.grenade_data.grenade_amount -= 1
        elif key == pygame.K_f and self.grenade_data.stun_grenade_amount > 0:
            self.stun_grenades.add(StunGrenade(*self._muzzle(), *self.aim))
            self.grenade_data.stun_grenade_amount -= 1
        elif key == pygame.K_r:
            self.ammo_count = self.gun.manual_reload()

    def _muzzle(self):
        return (
            (self.window[0] / 2.0) - self.camera_x,
            (self.window[1] / 2.0) - self.camera_y,
        )

    # ------------------------------------------------------------------
    # Simulation: one fixed step.
    # ------------------------------------------------------------------

    def step(self, pressed, dt=config.SIM_DT):
        if self.human.alive():
            self._walk(pressed, dt)

        self.previous_camera = self.camera
        self.camera_x = min(
            0, max(-(config.WORLD[0] - self.window[0]), self.camera_x + self.change_x)
        )
        self.camera_y = min(
            0, max(-(config.WORLD[1] - self.window[1]), self.camera_y + self.change_y)
        )

        if self.ammo_count == RELOAD:
            self.ammo_count = self.gun.reloading(dt)

        self._animate_player(dt)
        self._advance_zombies(dt)
        self._collect_powerups(dt)

        self.bullets.update(self.camera_x, self.camera_y, self.zombies, dt)
        self.grenades.update(self.camera_x, self.camera_y, self.explosions, dt)
        self.explosions.update(self.camera_x, self.camera_y, dt)
        self.stun_grenades.update(
            self.camera_x, self.camera_y, self.stun_explosions, dt
        )
        self.stun_explosions.update(self.camera_x, self.camera_y, dt)

        if not self.zombies:
            self.rules.advance(self.window, self.zombies, self.cash, dt, self.visible)

        self.instakill_seconds = max(0.0, self.instakill_seconds - dt)
        self.change_x = self.change_y = 0
        self.shooting = False

    def _walk(self, pressed, dt):
        if pressed[pygame.K_w]:
            self.change_y = config.PLAYER_SPEED * dt
        elif pressed[pygame.K_s]:
            self.change_y = -config.PLAYER_SPEED * dt
        if pressed[pygame.K_a]:
            self.change_x = config.PLAYER_SPEED * dt
        elif pressed[pygame.K_d]:
            self.change_x = -config.PLAYER_SPEED * dt

    def _animate_player(self, dt):
        # Preserves the original rule, quirks included: MOVE only when both
        # axes are positive, otherwise IDLE, and SHOOT overrides either.
        animation = "MOVE"
        if self.change_x <= 0 or self.change_y <= 0:
            animation = "IDLE"
        if self.shooting:
            animation = "SHOOT"
        self.human.update_anim(animation, dt)
        # Rotation resizes human.rect, which collision reads, so it has to
        # happen exactly once per step -- in the render pass it compounded with
        # frame rate and inflated the hitbox.
        self.human.rot_center(math.degrees(math.atan2(self.aim[1], self.aim[0])))

    def _advance_zombies(self, dt):
        for zombie in self.zombies:
            zombie.update_anim("MOVE", dt)
            is_zombie_attacking(self.human, zombie, dt)
            zombie.move_toward_center(self.camera_x, self.camera_y, dt)
            for explosion in self.explosions:
                explosion_touching_zombie(zombie, explosion)
            for stun_explosion in self.stun_explosions:
                stun_explosion_touching_zombie(zombie, stun_explosion)
            zombie.zombie_speed_timer(dt)

        keep_apart(self.zombies, self.camera, dt)

    def _collect_powerups(self, dt):
        for powerup in self.powerups:
            collected = powerup.update(self.human, self.camera_x, self.camera_y, dt)
            if collected is None:
                continue
            if collected != powerup_kinds.EXPIRED:
                self.instakill_seconds += collect_powerup(
                    collected, self.human, self.zombies, self.gun
                )
            powerup.kill()

    # ------------------------------------------------------------------
    # Render: once per frame, between steps.
    # ------------------------------------------------------------------

    def draw(self, screen, alpha):
        draw_x, draw_y = self._interpolated_camera(alpha)

        screen.blit(
            self.background.image_at(
                (0 - draw_x, 0 - draw_y, self.window[0], self.window[1])
            ),
            (0, 0),
        )

        blit_group(screen, self.powerups, draw_x, draw_y, alpha)
        for zombie in self.zombies:
            zombie.health_bar(screen, zombie.draw_position(draw_x, draw_y, alpha))
        blit_group(screen, self.zombies, draw_x, draw_y, alpha)
        self.human_group.draw(screen)
        blit_group(screen, self.bullets, draw_x, draw_y, alpha)

        if not self.zombies:
            self.rules.draw(screen, self.window)

        for group in (
            self.grenades,
            self.explosions,
            self.stun_grenades,
            self.stun_explosions,
        ):
            blit_group(screen, group, draw_x, draw_y, alpha)

        self._draw_overlays(screen)

    def _interpolated_camera(self, alpha):
        return (
            self.previous_camera[0] + (self.camera_x - self.previous_camera[0]) * alpha,
            self.previous_camera[1] + (self.camera_y - self.previous_camera[1]) * alpha,
        )

    def _draw_overlays(self, screen):
        self.radar.draw(
            screen,
            -self.camera_x + self.window[0] / 2,
            -self.camera_y + self.window[1] / 2,
        )
        for zombie in self.zombies:
            self.radar.update_zom(screen, zombie)

        if self.instakill_seconds > 0:
            centred_text(
                screen,
                self.window,
                f"INSTAKILL {int(self.instakill_seconds) + 1}s",
                INSTAKILL_TOP,
                size=34,
                colour=config.INSTAKILL_TEXT,
            )

        self.heads_up_display.update(screen, self.window)
        self.health_display.draw(screen, self.human.get_health())
        self.gun_display.draw(screen, self.gun)
        self.cash.update(screen, self.window)

        if self.ammo_count == RELOAD:
            centred_text(screen, self.window, "Reloading", RELOADING_TOP, size=30)
