import math
from functools import cache

import pygame

from shooter.assets import load_image, load_sound

GUN_SHOT = ("Sounds/gunAudio.wav", .01)
EXPLOSION = ("Sounds/explosion.wav", .01)


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

class Shot(pygame.sprite.Sprite):
    small_change_x=0
    small_change_y=0
    bullet_x=0
    bullet_y=0
    bullet_speed=150
    continuous=bullet_speed/14
    kill_me=False

    def __init__(self,start_x,start_y,x,y):
        pygame.sprite.Sprite.__init__(self)
        angle = math.atan2(y, x)  # find angle of shot
        self.small_change_x=math.cos(angle)
        self.small_change_y=-math.sin(angle)
        self.image = load_image("Projectiles/bullet.png", True)

        self.rect = self.image.get_rect()
        self.bullet_x = start_x - (self.rect[0] / 2)
        self.bullet_y = start_y - (self.rect[1] / 2)
        play(GUN_SHOT)



    def update(self,camera_x,camera_y,zombie_group):
        if not self.kill_me:
            for _ in range(int(self.continuous)):   #checks to see if bullet is touching zombie (bullet movement / bullet size) times
                self.rect.x=self.bullet_x+camera_x
                self.rect.y=self.bullet_y+camera_y
                self.bullet_x += (14 * self.small_change_x)
                self.bullet_y += (14 * self.small_change_y)
                for zombie in zombie_group:
                    if self.bullet_touching_zombie(zombie):
                        return
        else:
            self.kill()
        #kill bullet off screen
        if self.rect.x>1000 or self.rect.x<-1000 or self.rect.y>1000 or self.rect.y<-1000:
            self.kill_me=True

    def bullet_touching_zombie(self,zombie):
        if pygame.sprite.collide_rect(zombie, self):
            if zombie.remove_health(20):
                zombie.kill()
            self.kill_me=True
            return True




class Grenade(pygame.sprite.Sprite):
    change_x=0
    change_y=0
    grenade_x=0
    grenade_y=0
    x_counter=0
    y_counter=0
    explode=30

    def __init__(self, start_x, start_y, x, y):
        pygame.sprite.Sprite.__init__(self)
        angle = math.atan2(y, x)  # find angle of shot
        self.change_x = (int(50 * math.cos(angle)))  # x change amount
        self.change_y = (int(-50 * math.sin(angle)))  # Y change amount
        if self.change_x==0:
            self.change_x+=1
        if self.change_y == 0:
            self.change_y+=1
        self.image = load_image("Throwables/grenade.png", True)
        self.rect = self.image.get_rect()
        self.grenade_x = start_x - (self.rect[0]*1.0 / 2.0) #-half of grenade size
        self.grenade_y = start_y - (self.rect[1]*1.0 / 2.0)
        self.x_counter=x/self.change_x
        self.y_counter=-y/self.change_y


    def update(self, camera_x, camera_y, screen,explosions):
        #print self.x_counter, self.y_counter
        if self.explode==30:
            if self.x_counter>0:
                self.rect.x = self.grenade_x + camera_x
                self.grenade_x += self.change_x
                self.x_counter+= -1
            else:
                self.rect.x = self.grenade_x + camera_x
            if self.y_counter>0:
                self.rect.y = self.grenade_y + camera_y
                self.grenade_y += self.change_y
                self.y_counter+= -1
            else:
                self.rect.y = self.grenade_y + camera_y

            if self.x_counter<=0 and self.y_counter<=0:
                self.explode += -1
        else:
            if self.explode>0:
                self.rect.x = self.grenade_x + camera_x
                self.rect.y = self.grenade_y + camera_y
                self.explode += -1
            else:
                explosion=GrenadeDetonation(self.grenade_x,self.grenade_y)
                explosions.add(explosion)
                self.kill()


class GrenadeDetonation(pygame.sprite.Sprite):
    explosion_x=0
    explosion_y=0
    counter=1
    def __init__(self,start_x,start_y):
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image("Effects/explosion.png", True)
        self.rect = self.image.get_rect()
        self.explosion_x = start_x - (self.rect.size[0] / 2) #-half of explosion size
        self.explosion_y = start_y - (self.rect.size[1] / 2)
        play(EXPLOSION)

    def update(self, camera_x, camera_y):
        #times before kill
        if self.counter>0:
            self.rect.x=self.explosion_x+camera_x
            self.rect.y = self.explosion_y + camera_y
            self.counter+= -1
        else:
            self.kill()


class StunGrenade(pygame.sprite.Sprite):
    change_x=0
    change_y=0
    grenade_x=0
    grenade_y=0
    x_counter=0
    y_counter=0
    explode=30

    def __init__(self, start_x, start_y, x, y):
        pygame.sprite.Sprite.__init__(self)
        angle = math.atan2(y, x)  # find angle of shot
        self.change_x = (int(50 * math.cos(angle)))  # x change amount
        self.change_y = (int(-50 * math.sin(angle)))  # Y change amount
        if self.change_x==0:
            self.change_x+=1
        if self.change_y == 0:
            self.change_y+=1
        self.image = load_image("Throwables/stungrenade.png", True)
        self.rect = self.image.get_rect()
        self.grenade_x = start_x - (self.rect[0]*1.0 / 2.0) #-half of grenade size
        self.grenade_y = start_y - (self.rect[1]*1.0 / 2.0)
        self.x_counter=x/self.change_x
        self.y_counter=-y/self.change_y


    def update(self, camera_x, camera_y, screen,explosions):
        if self.explode==30:
            if self.x_counter>0:
                self.rect.x = self.grenade_x + camera_x
                self.grenade_x += self.change_x
                self.x_counter+= -1
            else:
                self.rect.x = self.grenade_x + camera_x
            if self.y_counter>0:
                self.rect.y = self.grenade_y + camera_y
                self.grenade_y += self.change_y
                self.y_counter+= -1
            else:
                self.rect.y = self.grenade_y + camera_y
            if self.x_counter<=0 and self.y_counter<=0:
                self.explode += -1
        else:
            if self.explode>0:
                self.rect.x = self.grenade_x + camera_x
                self.rect.y = self.grenade_y + camera_y
                self.explode += -1
            else:
                explosion=StunDetonation(self.grenade_x,self.grenade_y)
                explosions.add(explosion)
                self.kill()


class StunDetonation(pygame.sprite.Sprite):
    explosion_x=0
    explosion_y=0
    counter=1
    def __init__(self,start_x,start_y):
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image("Effects/stunexplosion.png", True)
        self.rect = self.image.get_rect()
        self.explosion_x = start_x - (self.rect.size[0] / 2) #-half of explosion size
        self.explosion_y = start_y - (self.rect.size[1] / 2)
        play(EXPLOSION)

    def update(self, camera_x, camera_y):
        #times before kill
        if self.counter>0:
            self.rect.x=self.explosion_x+camera_x
            self.rect.y = self.explosion_y + camera_y
            self.counter+= -1
        else:
            self.kill()
