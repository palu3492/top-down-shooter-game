import math
import random

import pygame

from shooter import config
from shooter.assets import load_animation, load_sized
from shooter.render import Interpolated

ANIMATIONS = {
    "IDLE": ("Zombie Animations/zombie_idle", "skeleton-idle_", 17),
    "MOVE": ("Zombie Animations/zombie_move", "skeleton-move_", 17),
    "ATTACK": ("Zombie Animations/zombie_attack", "skeleton-attack_", 9),
}


class Zombie(Interpolated, pygame.sprite.Sprite):
    def __init__(self, window_size, cash):
        self.player_cash = cash
        pygame.sprite.Sprite.__init__(self)
        self.zombie_x = self.zombie_y = 0
        self.type = "MOVE"
        self.current_idle = self.current_move = self.current_attack = 0
        self.zombie_speed = config.ZOMBIE_SPEED
        self.stun_seconds = 0.0
        self.animation_clock = 0.0
        self.zombie_health = config.ZOMBIE_HEALTH
        self.window_size = window_size
        self.frames = {
            name: load_animation(directory, prefix, count, config.ZOMBIE_SCALE, True)
            for name, (directory, prefix, count) in ANIMATIONS.items()
        }
        self.image = load_sized(
            "Zombie Animations/zombie_idle/skeleton-idle_0.png",
            *config.ZOMBIE_SIZE,
            True,
        )
        self.rect = self.image.get_rect()
        self.spawn_zombie()  # calls function that controls Zombie Spawning
        self.remember_position()

    # Spawns zombies out side of screen size
    def spawn_zombie(self):
        width, height = config.SPAWN_AREA
        selection = random.randint(1, 4)
        if selection == 1:
            self.zombie_y = -1
            self.zombie_x = random.randint(0, width)
        elif selection == 2:
            self.zombie_y = height + 1
            self.zombie_x = random.randint(0, width)
        elif selection == 3:
            self.zombie_y = random.randint(0, height)
            self.zombie_x = -1
        elif selection == 4:
            self.zombie_y = random.randint(0, height)
            self.zombie_x = width + 1

    def update_anim(self, type, dt=1 / config.ANIMATION_FPS):
        if type != "Null":
            self.type = type

        self.animation_clock += dt * config.ANIMATION_FPS
        steps, self.animation_clock = divmod(self.animation_clock, 1)
        for _ in range(int(steps)):
            self._advance()
        self._show()

    def _advance(self):

        if self.type == "IDLE":
            if self.current_idle < 16:
                self.current_idle += 1
            else:
                self.current_idle = 0
        elif self.type == "MOVE":
            if self.current_move < 16:
                self.current_move += 1
            else:
                self.current_move = 0
        elif self.type == "ATTACK":
            if self.current_attack < 8:
                self.current_attack += 1
            else:
                self.current_attack = 0

    def _show(self):
        frame = {
            "IDLE": self.current_idle,
            "MOVE": self.current_move,
            "ATTACK": self.current_attack,
        }[self.type]
        self.image = self.frames[self.type][frame]
        self.rect = self.image.get_rect(topleft=self.rect.topleft)

    @property
    def world_x(self):
        return self.zombie_x

    @property
    def world_y(self):
        return self.zombie_y

    def get_position(self):
        return (self.zombie_x, self.zombie_y)

    def set_position(self, x, y):
        self.zombie_y = y
        self.zombie_x = x

    def move_y(self, y):
        self.rect.y += y

    def move_x(self, x):
        self.rect.x += x

    def reset_position(self):
        self.spawn_zombie()

    def move_position(self, camera_x, camera_y):
        self.rect.x = self.zombie_x + camera_x
        self.rect.y = self.zombie_y + camera_y

    def move_toward_center(self, camera_x, camera_y, dt=config.SIM_DT):
        self.remember_position()
        zombie_pos = self.rect.x, self.rect.y
        distance_from_center_x = (self.window_size[0] / 2.0) - zombie_pos[0] - 120
        distance_from_center_y = (self.window_size[1] / 2.0) - zombie_pos[1] - 110
        angle = math.atan2(
            distance_from_center_x, distance_from_center_y
        )  # find angle of zombie toward center
        move_x_amount = self.zombie_speed * math.sin(angle) * dt
        move_y_amount = self.zombie_speed * math.cos(angle) * dt
        self.zombie_x += move_x_amount
        self.zombie_y += move_y_amount
        self.move_position(camera_x, camera_y)

    def health_bar(self, screen, at=None):
        x, y = at if at else self.rect.topleft
        pygame.draw.rect(
            screen,
            config.HEALTH_RED,
            (x + 75, y, self.zombie_health * 1.2, 22),
        )
        pygame.draw.rect(
            screen,
            config.HEALTH_GREY,
            (x + 75, y, 100 * 1.2, 22),
            4,
        )

    def remove_health(self, damage):
        if self.zombie_health <= 0:
            return False
        self.zombie_health -= damage
        if self.zombie_health <= 0:
            self.player_cash.increase_cash(config.KILL_REWARD)
            return True
        return False

    def add_health(self, repair):
        self.zombie_health += repair

    def remove_speed(self, stun_amount):
        self.zombie_speed = stun_amount
        self.stun_seconds = config.STUN_SECONDS

    def zombie_speed_timer(self, dt=config.SIM_DT):
        if self.stun_seconds > 0:
            self.stun_seconds -= dt
        else:
            self.zombie_speed = config.ZOMBIE_SPEED
