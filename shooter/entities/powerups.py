import random

import pygame

from shooter import config
from shooter.assets import load_image
from shooter.render import Interpolated

INSTAKILL, NUKE, MAX_AMMO, MAX_HEALTH = 1, 2, 3, 4
EXPIRED = "EXPIRED"
LIFETIME = config.POWERUP_LIFETIME_SECONDS


class PowerUps(Interpolated, pygame.sprite.Sprite):
    def spawning_location(self):
        # A real world position, like every other entity. It used to accumulate
        # camera deltas into rect, which left nothing to interpolate from.
        self.world_x, self.world_y = config.POWERUP_SPAWN
        self.remember_position()
        self.rect.topleft = config.POWERUP_SPAWN

    def follow_camera(self, camera_x, camera_y):
        self.remember_position()
        self.rect.topleft = (self.world_x + camera_x, self.world_y + camera_y)

    def instakill(self):
        self.image = load_image("Power Ups/instakill.png")
        self.rect = self.image.get_rect()
        self.spawning_location()

    def nuke(self):
        self.image = load_image("Power Ups/Nuke.png")
        self.rect = self.image.get_rect()
        self.spawning_location()

    def max_ammo(self):
        self.image = load_image("Power Ups/MaxAmmo.png")
        self.rect = self.image.get_rect()
        self.spawning_location()

    def max_health(self):
        self.image = load_image("Power Ups/MaxHealth.png")
        self.rect = self.image.get_rect()
        self.spawning_location()

    def select_powerup(self):
        self.powerup_selected = self.rng.randint(INSTAKILL, MAX_HEALTH)
        if self.powerup_selected == 1:
            self.instakill()
        elif self.powerup_selected == 2:
            self.nuke()
        elif self.powerup_selected == 3:
            self.max_ammo()
        elif self.powerup_selected == 4:
            self.max_health()

    def tick(self, dt=config.SIM_DT):
        if self.alive_seconds == 0:
            self.og_image = self.image
            self.blank_image = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        if self.alive_seconds >= config.POWERUP_BLINK_AFTER:
            blinking = any(
                start <= self.alive_seconds <= end
                for start, end in config.POWERUP_BLINK_WINDOWS
            )
            self.image = self.blank_image if blinking else self.og_image
        if self.alive_seconds >= LIFETIME:
            return EXPIRED
        self.alive_seconds += dt
        return None

    def update(self, human, camera_x, camera_y, dt=config.SIM_DT):
        """Return the kind collected, EXPIRED, or None if still on the field.

        Applying the effect is the caller's job -- a pickup that reached into
        the zombie group, the gun and the player would know about everything.
        """
        self.follow_camera(camera_x, camera_y)
        if pygame.sprite.collide_rect(human, self):
            return self.powerup_selected
        return self.tick(dt)

    def __init__(self, rng=None):
        self.rng = random if rng is None else rng
        pygame.sprite.Sprite.__init__(self)
        self.powerup_selected = 0
        self.alive_seconds = 0.0
        self.og_image = None
        self.blank_image = None
        self.select_powerup()
        self.image = pygame.transform.scale(
            self.image,
            (
                int(self.image.get_rect().size[0] * 0.5),
                int(self.image.get_rect().size[1] * 0.5),
            ),
        )
