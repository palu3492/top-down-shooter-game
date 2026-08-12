import pygame

from shooter.assets import load_animation

from shooter import config

ANIMATIONS = {
    "IDLE": ("Player Animations/Idle", "survivor-idle_rifle_", 20),
    "MOVE": ("Player Animations/Move", "survivor-move_rifle_", 20),
    "SHOOT": ("Player Animations/Shoot", "survivor-shoot_rifle_", 3),
}


class Human(pygame.sprite.Sprite):
    type = "IDLE"
    current_idle = 0
    current_move = 0
    current_shoot = 0

    player_cash = 0

    health = config.PLAYER_HEALTH

    def __init__(self, window_size):
        pygame.sprite.Sprite.__init__(self)
        self.frames = {
            name: load_animation(directory, prefix, count, config.PLAYER_SCALE)
            for name, (directory, prefix, count) in ANIMATIONS.items()
        }
        self.image = self.frames["IDLE"][0]
        self.rect = self.image.get_rect()
        self.rect.x = (window_size[0] / 2.0) - (self.rect.size[0] / 2.0)
        self.rect.y = (window_size[1] / 2.0) - (self.rect.size[1] / 2.0)

    def rot_center(self, angle):
        """Rotate the current frame about its centre."""
        centre = self.rect.center
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=centre)

    def update_anim(
        self,
        type,
    ):
        self.type = type
        frame = 0
        if self.type == "IDLE":
            if self.current_idle < 19:
                self.current_idle += 1
            else:
                self.current_idle = 0
            frame = self.current_idle
        elif type == "MOVE":
            if self.current_move < 19:
                self.current_move += 1
            else:
                self.current_move = 0
            frame = self.current_move
        elif type == "SHOOT":
            if self.current_shoot < 2:
                self.current_shoot += 1
            else:
                self.current_shoot = 0
            frame = self.current_shoot

        self.image = self.frames[type][frame]
        self.health_regen()

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

    def health_regen(self):
        if self.health < config.PLAYER_HEALTH:
            self.health += config.PLAYER_REGEN
