import pygame

from shooter.assets import load_scaled

from shooter import config

PLAYER_IMAGE = "Player Animations/Idle Knife/survivor-idle_knife_0.png"


class Human(pygame.sprite.Sprite):
    def __init__(self, window_size):
        pygame.sprite.Sprite.__init__(self)
        self.health = config.PLAYER_HEALTH
        self.base_image = load_scaled(PLAYER_IMAGE, config.PLAYER_SCALE, True)
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.recentre(window_size)

    def recentre(self, window_size):
        """The player is always drawn at the middle of the screen, so a change
        of resolution moves them rather than leaving them off to one side."""
        self.rect.x = (window_size[0] / 2.0) - (self.rect.size[0] / 2.0)
        self.rect.y = (window_size[1] / 2.0) - (self.rect.size[1] / 2.0)

    def rot_center(self, angle):
        """Rotate the current frame about its centre."""
        centre = self.rect.center
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=centre)

    def update_anim(self, type, dt=1 / config.ANIMATION_FPS, weapon_id=None):
        """Keep one sprite for every action and weapon while animations are off."""
        centre = self.rect.center
        self.image = self.base_image
        self.rect = self.image.get_rect(center=centre)
        self.health_regen(dt)

    def remove_health(self, damage):
        self.health -= damage
        return self.health <= 0

    def add_health(self, repair):
        self.health += repair

    def restore_health(self):
        self.health = config.PLAYER_HEALTH

    def get_health(self):
        if self.health > 0:
            return int(self.health)
        else:
            return 0

    def health_regen(self, dt=config.SIM_DT):
        if self.health < config.PLAYER_HEALTH:
            self.health = min(
                config.PLAYER_HEALTH, self.health + config.PLAYER_REGEN * dt
            )
