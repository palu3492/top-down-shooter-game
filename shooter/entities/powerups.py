import random

import pygame

from shooter import config
from shooter.assets import load_image

INSTAKILL, NUKE, MAX_AMMO, MAX_HEALTH = 1, 2, 3, 4
EXPIRED = "EXPIRED"
LIFETIME = config.POWERUP_LIFETIME_FRAMES


class PowerUps(pygame.sprite.Sprite):
    powerup_selected = 0

    timer_count = 0

    def spawning_location(self):
        self.rect.x, self.rect.y = config.POWERUP_SPAWN

    def move_with_camera(self, x, y):
        self.rect.y = self.rect.y + y
        self.rect.x = self.rect.x + x

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
        self.powerup_selected = random.randint(INSTAKILL, MAX_HEALTH)
        if self.powerup_selected == 1:
            self.instakill()
        elif self.powerup_selected == 2:
            self.nuke()
        elif self.powerup_selected == 3:
            self.max_ammo()
        elif self.powerup_selected == 4:
            self.max_health()

    def tick(self):
        if self.timer_count == 0:
            self.og_image = self.image
            self.blank_image = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        if self.timer_count >= config.POWERUP_BLINK_AFTER:
            if (
                (self.timer_count >= 400 and self.timer_count <= 500)
                or (self.timer_count >= 600 and self.timer_count <= 650)
                or (self.timer_count >= 800 and self.timer_count <= 850)
                or (self.timer_count >= 1000 and self.timer_count <= 1050)
                or (self.timer_count >= 1100 and self.timer_count <= 1125)
                or (self.timer_count >= 1150 and self.timer_count <= 1175)
            ):
                self.image = self.blank_image
            else:
                self.image = self.og_image
        if self.timer_count >= LIFETIME:
            return EXPIRED
        self.timer_count += 1
        return None

    def update(self, human, change_x, change_y):
        """Return the kind collected, EXPIRED, or None if still on the field.

        Applying the effect is the caller's job -- a pickup that reached into
        the zombie group, the gun and the player would know about everything.
        """
        self.move_with_camera(change_x, change_y)
        if pygame.sprite.collide_rect(human, self):
            return self.powerup_selected
        return self.tick()

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.select_powerup()
        self.image = pygame.transform.scale(
            self.image,
            (
                int(self.image.get_rect().size[0] * 0.5),
                int(self.image.get_rect().size[1] * 0.5),
            ),
        )
