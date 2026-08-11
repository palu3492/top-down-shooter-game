import pygame

class Human(pygame.sprite.Sprite):

    type = "IDLE"
    current_idle = 0
    current_move = 0
    current_shoot = 0

    player_cash = 0

    health = 100.00

    player = "Assets/Player Animations/" + type + "/survivor-" + type + "_rifle_" + str(0) + ".png"

    def __init__(self, window_size):
       pygame.sprite.Sprite.__init__(self)
       self.image = pygame.image.load("Assets/Player Animations/Idle/survivor-idle_rifle_0.png")
       self.image = pygame.transform.scale(self.image, (int(self.image.get_rect().size[0] * .5),int(self.image.get_rect().size[1] * .5)))
       self.rect = self.image.get_rect()
       self.rect.x = (window_size[0] / 2.0) - (self.rect.size[0] / 2.0)
       self.rect.y = (window_size[1]/2.0)-(self.rect.size[1]/2.0)

    def rot_center(self, angle):

        """rotate an image while keeping its center"""
        rot_image = pygame.transform.rotate(self.image, angle)
        self.image = rot_image

        # orig_rect = self.image.get_rect()
        # rot_image = pygame.transform.rotate(self.image, angle)
        # rot_rect = orig_rect.copy()
        # rot_rect.center = rot_image.get_rect().center
        # rot_image = rot_image.subsurface(rot_rect).copy()
        # self.image = rot_image

    def update_anim(self, type,):
        self.type = type
        if self.type == "IDLE":
            if self.current_idle < 19:
                self.current_idle+=1
            else:
                self.current_idle = 0
            self.player = "Assets/Player Animations/" + type + "/survivor-" + type + "_rifle_" + "0" + ".png"
        elif type == "MOVE":
            if self.current_move < 19:
                self.current_move += 1
            else:
                self.current_move = 0
            self.player = "Assets/Player Animations/" + type + "/survivor-" + type + "_rifle_" + str(self.current_move) + ".png"
        elif type == "SHOOT":
            if self.current_shoot < 2:
                self.current_shoot += 1
            else:
                self.current_shoot = 0
            self.player = "Assets/Player Animations/" + type + "/survivor-" + type + "_rifle_" + str(self.current_shoot) + ".png"

        self.image = pygame.image.load(self.player)
        self.image = pygame.transform.scale(self.image, (int(self.image.get_rect().size[0] * .5),int(self.image.get_rect().size[1] * .5)))
        self.health_regen()

    def remove_health(self, damage):
        self.health -= damage
        if self.health <= 0:
            return True
        else:
            return False

    def add_health(self, repair):
        self.health += repair

    def get_health(self):
        if self.health > 0:
            return  int(self.health)
        else:
            return 0

    def health_regen(self):
        if self.health < 100:
            self.health += .05




