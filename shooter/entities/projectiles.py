import math
from functools import cache

import pygame

from shooter import config
from shooter.assets import load_image, load_sound
from shooter.render import Interpolated

BULLET_DAMAGE = config.BULLET_DAMAGE
LETHAL = config.LETHAL

GUN_SHOT = ("Sounds/gunAudio.wav", 0.01)
EXPLOSION = ("Sounds/explosion.wav", 0.01)


@cache
def _load(name, volume):
    sound = load_sound(name)
    sound.set_volume(volume)
    return sound


def play(spec):
    """Play a sound, or do nothing if there is no usable audio device.

    Loading is deferred to first use so that importing this module has no side
    effects -- pygame.mixer.init() at import time took the whole game down on
    machines without audio.
    """
    if not pygame.mixer.get_init():
        return
    _load(*spec).play()


class Shot(Interpolated, pygame.sprite.Sprite):
    SPEED = config.BULLET_SPEED

    def __init__(self, start_x, start_y, x, y, damage=BULLET_DAMAGE):
        pygame.sprite.Sprite.__init__(self)
        self.damage = damage
        self.kill_me = False
        angle = math.atan2(y, x)  # find angle of shot
        self.small_change_x = math.cos(angle)
        self.small_change_y = -math.sin(angle)
        self.image = load_image("Projectiles/bullet.png", True)

        self.rect = self.image.get_rect()
        self.bullet_x = start_x - (self.rect[0] / 2)
        self.bullet_y = start_y - (self.rect[1] / 2)
        self.remember_position()
        play(GUN_SHOT)

    def update(self, camera_x, camera_y, zombie_group, dt=config.SIM_DT):
        self.remember_position()
        if not self.kill_me:
            # Sub-step by distance so a fast shot cannot tunnel past a zombie,
            # and so the step count follows the frame length instead of fixing it.
            distance = self.SPEED * dt
            steps = max(1, math.ceil(distance / config.BULLET_STEP))
            step = distance / steps
            for _ in range(steps):
                self.rect.x = self.bullet_x + camera_x
                self.rect.y = self.bullet_y + camera_y
                self.bullet_x += step * self.small_change_x
                self.bullet_y += step * self.small_change_y
                for zombie in zombie_group:
                    if self.bullet_touching_zombie(zombie):
                        return
        else:
            self.kill()
        # kill bullet off screen
        if (
            self.rect.x > config.BULLET_RANGE
            or self.rect.x < -config.BULLET_RANGE
            or self.rect.y > config.BULLET_RANGE
            or self.rect.y < -config.BULLET_RANGE
        ):
            self.kill_me = True

    @property
    def world_x(self):
        return self.bullet_x

    @property
    def world_y(self):
        return self.bullet_y

    def bullet_touching_zombie(self, zombie):
        if pygame.sprite.collide_rect(zombie, self):
            if zombie.remove_health(self.damage):
                zombie.kill()
            self.kill_me = True
            return True


class Grenade(Interpolated, pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.explode = config.GRENADE_FUSE
        angle = math.atan2(y, x)  # find angle of shot
        self.change_x = config.GRENADE_SPEED * math.cos(angle)
        self.change_y = -config.GRENADE_SPEED * math.sin(angle)
        self.image = load_image("Throwables/grenade.png", True)
        self.rect = self.image.get_rect()
        self.grenade_x = start_x - (self.rect[0] * 1.0 / 2.0)  # -half of grenade size
        self.grenade_y = start_y - (self.rect[1] * 1.0 / 2.0)
        self.travelled = 0.0
        self.flight = math.hypot(x, y) / config.GRENADE_SPEED
        self.remember_position()

    @property
    def world_x(self):
        return self.grenade_x

    @property
    def world_y(self):
        return self.grenade_y

    def update(self, camera_x, camera_y, explosions, dt=config.SIM_DT):
        self.remember_position()
        if self.travelled < self.flight:
            step = min(dt, self.flight - self.travelled)
            self.grenade_x += self.change_x * step
            self.grenade_y += self.change_y * step
            self.travelled += step
        else:
            self.explode -= dt
            if self.explode <= 0:
                explosions.add(GrenadeDetonation(self.grenade_x, self.grenade_y))
                self.kill()
                return
        self.rect.x = self.grenade_x + camera_x
        self.rect.y = self.grenade_y + camera_y


class GrenadeDetonation(Interpolated, pygame.sprite.Sprite):
    def __init__(self, start_x, start_y):
        pygame.sprite.Sprite.__init__(self)
        self.life = config.EXPLOSION_SECONDS
        self.image = load_image("Effects/explosion.png", True)
        self.rect = self.image.get_rect()
        self.explosion_x = start_x - (self.rect.size[0] / 2)  # -half of explosion size
        self.explosion_y = start_y - (self.rect.size[1] / 2)
        play(EXPLOSION)

        self.remember_position()

    @property
    def world_x(self):
        return self.explosion_x

    @property
    def world_y(self):
        return self.explosion_y

    def update(self, camera_x, camera_y, dt=config.SIM_DT):
        if self.life > 0:
            self.rect.x = self.explosion_x + camera_x
            self.rect.y = self.explosion_y + camera_y
            self.life -= dt
        else:
            self.kill()


class StunGrenade(Interpolated, pygame.sprite.Sprite):
    def __init__(self, start_x, start_y, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.explode = config.GRENADE_FUSE
        angle = math.atan2(y, x)  # find angle of shot
        self.change_x = config.GRENADE_SPEED * math.cos(angle)
        self.change_y = -config.GRENADE_SPEED * math.sin(angle)
        self.image = load_image("Throwables/stungrenade.png", True)
        self.rect = self.image.get_rect()
        self.grenade_x = start_x - (self.rect[0] * 1.0 / 2.0)  # -half of grenade size
        self.grenade_y = start_y - (self.rect[1] * 1.0 / 2.0)
        self.travelled = 0.0
        self.flight = math.hypot(x, y) / config.GRENADE_SPEED
        self.remember_position()

    @property
    def world_x(self):
        return self.grenade_x

    @property
    def world_y(self):
        return self.grenade_y

    def update(self, camera_x, camera_y, explosions, dt=config.SIM_DT):
        self.remember_position()
        if self.travelled < self.flight:
            step = min(dt, self.flight - self.travelled)
            self.grenade_x += self.change_x * step
            self.grenade_y += self.change_y * step
            self.travelled += step
        else:
            self.explode -= dt
            if self.explode <= 0:
                explosions.add(StunDetonation(self.grenade_x, self.grenade_y))
                self.kill()
                return
        self.rect.x = self.grenade_x + camera_x
        self.rect.y = self.grenade_y + camera_y


class StunDetonation(Interpolated, pygame.sprite.Sprite):
    def __init__(self, start_x, start_y):
        pygame.sprite.Sprite.__init__(self)
        self.life = config.EXPLOSION_SECONDS
        self.image = load_image("Effects/stunexplosion.png", True)
        self.rect = self.image.get_rect()
        self.explosion_x = start_x - (self.rect.size[0] / 2)  # -half of explosion size
        self.explosion_y = start_y - (self.rect.size[1] / 2)
        play(EXPLOSION)

        self.remember_position()

    @property
    def world_x(self):
        return self.explosion_x

    @property
    def world_y(self):
        return self.explosion_y

    def update(self, camera_x, camera_y, dt=config.SIM_DT):
        if self.life > 0:
            self.rect.x = self.explosion_x + camera_x
            self.rect.y = self.explosion_y + camera_y
            self.life -= dt
        else:
            self.kill()
