import math
import random

import pygame

from shooter.assets import load_animation, load_sized

ANIMATIONS = {
    "IDLE": ("Zombie Animations/zombie_idle", "skeleton-idle_", 17),
    "MOVE": ("Zombie Animations/zombie_move", "skeleton-move_", 17),
    "ATTACK": ("Zombie Animations/zombie_attack", "skeleton-attack_", 9),
}


class Zombie(pygame.sprite.Sprite):
    zombie_x = zombie_y = 0
    type = "MOVE"
    current_idle, current_move, current_attack = 0, 0, 0
    zombie_speed = 6
    stun_timer = 0

    zombie_health = 100.00

    def __init__(self, window_size, cash):
        self.player_cash = cash
        pygame.sprite.Sprite.__init__(self)
        self.window_size = window_size
        self.frames = {
            name: load_animation(directory, prefix, count, 0.5, True)
            for name, (directory, prefix, count) in ANIMATIONS.items()
        }
        self.image = load_sized(
            "Zombie Animations/zombie_idle/skeleton-idle_0.png", 120, 111, True
        )
        self.rect = self.image.get_rect()
        self.spawn_zombie()  # calls function that controls Zombie Spawning

    # Spawns zombies out side of screen size
    def spawn_zombie(self):
        selection = random.randint(1, 4)
        if selection == 1:
            self.zombie_y = -1
            self.zombie_x = random.randint(1, 192) * 10
        elif selection == 2:
            self.zombie_y = 1081
            self.zombie_x = random.randint(1, 192) * 10
        elif selection == 3:
            self.zombie_y = random.randint(1, 108) * 10
            self.zombie_x = -1
        elif selection == 4:
            self.zombie_y = random.randint(1, 108) * 10
            self.zombie_x = 1921

    def update_anim(self, type):
        if type == "Null":
            pass
        else:
            self.type = type

        frame = 0
        if self.type == "IDLE":
            if self.current_idle < 16:
                self.current_idle += 1
            else:
                self.current_idle = 0
            frame = self.current_idle
        elif self.type == "MOVE":
            if self.current_move < 16:
                self.current_move += 1
            else:
                self.current_move = 0
            frame = self.current_move
        elif self.type == "ATTACK":
            if self.current_attack < 8:
                self.current_attack += 1
            else:
                self.current_attack = 0
            frame = self.current_attack

        self.image = self.frames[self.type][frame]
        self.rect = self.image.get_rect(topleft=self.rect.topleft)

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

    def move_toward_center(self, camera_x, camera_y):
        zombie_pos = self.rect.x, self.rect.y
        distance_from_center_x = (self.window_size[0] / 2.0) - zombie_pos[0] - 120
        distance_from_center_y = (self.window_size[1] / 2.0) - zombie_pos[1] - 110
        angle = math.atan2(
            distance_from_center_x, distance_from_center_y
        )  # find angle of zombie toward center
        move_x_amount = self.zombie_speed * math.sin(angle)  # x change amount
        move_y_amount = self.zombie_speed * math.cos(angle)  # Y change amount
        self.zombie_x += move_x_amount
        self.zombie_y += move_y_amount
        self.move_position(camera_x, camera_y)

    def health_bar(self, screen):
        pygame.draw.rect(
            screen,
            (244, 66, 66),
            (self.rect.x + 75, self.rect.y, self.zombie_health * 1.2, 22),
        )
        pygame.draw.rect(
            screen, (96, 96, 96), (self.rect.x + 75, self.rect.y, 100 * 1.2, 22), 4
        )

    def remove_health(self, damage):
        if self.zombie_health <= 0:
            return False
        self.zombie_health -= damage
        if self.zombie_health <= 0:
            self.player_cash.increase_cash(50)
            return True
        return False

    def add_health(self, repair):
        self.zombie_health += repair

    def remove_speed(self, stun_amount):
        self.zombie_speed = stun_amount
        self.stun_timer = 200

    def zombie_speed_timer(self):
        if self.stun_timer > 0:
            self.stun_timer -= 1
        else:
            self.zombie_speed = 6
