import pygame
import random
class PowerUps(pygame.sprite.Sprite):

    # 0 == Null
    # 1 == InstaKill
    # 2 == Nuke
    # 3 == MaxAmmo
    # 4 == MaxHealth
    powerup_selected = 0

    og_image = pygame.image.load("Assets/Power Ups/MaxHealth.png")

    timer_count = 0

    def Spawning_Location(self):
        self.rect.y = 500
        self.rect.x = 800

    def Move_With_Camera(self, X, Y):
        self.rect.y = self.rect.y + Y
        self.rect.x = self.rect.x + X

    def InstaKill(self):
        self.image = pygame.image.load("Assets/Power Ups/instakill.png")
        self.rect = self.image.get_rect()
        self.Spawning_Location()

    def Nuke(self):
        self.image = pygame.image.load("Assets/Power Ups/Nuke.png")
        self.rect = self.image.get_rect()
        self.Spawning_Location()

    def MaxAmmo(self):
        self.image = pygame.image.load("Assets/Power Ups/MaxAmmo.png")
        self.rect = self.image.get_rect()
        self.Spawning_Location()

    def MaxHealth(self):
        self.image = pygame.image.load("Assets/Power Ups/MaxHealth.png")
        self.rect = self.image.get_rect()
        self.Spawning_Location()

    def PowerUp_Selection(self):
        self.powerup_selected = random.randint(2,2)
        if self.powerup_selected == 1:
            self.InstaKill()
        elif self.powerup_selected == 2:
            self.Nuke()
        elif self.powerup_selected == 3:
            self.MaxAmmo()
        elif self.powerup_selected == 4:
            self.MaxHealth()

    def Timer(self, screen):
        if self.timer_count == 0:
            self.og_image = self.image
        if self.timer_count >= 400:
            if (self.timer_count >= 400 and self.timer_count <= 500) or\
                    (self.timer_count >= 600 and self.timer_count <= 650) or\
                    (self.timer_count >= 800 and self.timer_count <= 850) or\
                    (self.timer_count >= 1000 and self.timer_count <= 1050) or\
                    (self.timer_count >= 1100 and self.timer_count <= 1125) or\
                    (self.timer_count >= 1150 and self.timer_count <= 1175):
                self.image = pygame.image.load("Human.png")
                self.image = pygame.transform.scale\
                    (self.image, (int(self.image.get_rect().size[0] * .1), int(self.image.get_rect().size[1] * .1)))
            else:
                self.image = self.og_image
        if self.timer_count >= 1200:
            return True
        else:
            self.timer_count +=1
            return False


    def update(self, human, zombie_group, screen, changeX, changeY):
        self.Move_With_Camera(changeX, changeY)
        if pygame.sprite.collide_rect(human, self):
            if self.powerup_selected == 2:
                zombie_group.empty()
            elif self.powerup_selected == 1:
                pass
            return True
        else:
            return self.Timer(screen)

    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.PowerUp_Selection()
        self.image = pygame.transform.scale(self.image, (int(self.image.get_rect().size[0] * .5), int(self.image.get_rect().size[1] * .5)))



