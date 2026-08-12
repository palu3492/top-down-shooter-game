import pygame
import random

from shooter.assets import load_image
class PowerUps(pygame.sprite.Sprite):

    # 0 == Null
    # 1 == instakill
    # 2 == nuke
    # 3 == max_ammo
    # 4 == max_health
    powerup_selected = 0

    timer_count = 0

    def spawning_location(self):
        self.rect.y = 500
        self.rect.x = 800

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
        self.powerup_selected = random.randint(2,2)
        if self.powerup_selected == 1:
            self.instakill()
        elif self.powerup_selected == 2:
            self.nuke()
        elif self.powerup_selected == 3:
            self.max_ammo()
        elif self.powerup_selected == 4:
            self.max_health()

    def tick(self, screen):
        if self.timer_count == 0:
            self.og_image = self.image
            self.blank_image = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        if self.timer_count >= 400:
            if (self.timer_count >= 400 and self.timer_count <= 500) or\
                    (self.timer_count >= 600 and self.timer_count <= 650) or\
                    (self.timer_count >= 800 and self.timer_count <= 850) or\
                    (self.timer_count >= 1000 and self.timer_count <= 1050) or\
                    (self.timer_count >= 1100 and self.timer_count <= 1125) or\
                    (self.timer_count >= 1150 and self.timer_count <= 1175):
                self.image = self.blank_image
            else:
                self.image = self.og_image
        if self.timer_count >= 1200:
            return True
        else:
            self.timer_count +=1
            return False


    def update(self, human, zombie_group, screen, change_x, change_y):
        self.move_with_camera(change_x, change_y)
        if pygame.sprite.collide_rect(human, self):
            if self.powerup_selected == 2:
                zombie_group.empty()
            elif self.powerup_selected == 1:
                pass
            return True
        else:
            return self.tick(screen)

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.select_powerup()
        self.image = pygame.transform.scale(self.image, (int(self.image.get_rect().size[0] * .5), int(self.image.get_rect().size[1] * .5)))



