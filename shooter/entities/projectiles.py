import pygame
import math

pygame.mixer.init()
gun_shot_sound = pygame.mixer.Sound('Assets/Sounds/gunAudio.wav')
gun_shot_sound.set_volume(.01)
explosion_sound = pygame.mixer.Sound('Assets/Sounds/explosion.wav')
explosion_sound.set_volume(.01)

class Shot(pygame.sprite.Sprite):
    smallChangeX=0
    smallChangeY=0
    changeX=0
    changeY=0
    bulletX=0
    bulletY=0
    bullet_speed=150
    continuous=bullet_speed/14
    kill_me=False
    
    def __init__(self,startX,startY,x,y):
        pygame.sprite.Sprite.__init__(self)
        angle = math.atan2(y, x)  # find angle of shot
        self.smallChangeX=math.cos(angle)
        self.smallChangeY=-math.sin(angle)
        self.changeX = int(self.bullet_speed * self.smallChangeX)  # x change amount
        self.changeY = int(self.bullet_speed * self.smallChangeX)  # Y change amount

        self.image = pygame.image.load("Assets/Projectiles/bullet.png").convert_alpha()

        self.rect = self.image.get_rect()
        self.bulletX = startX - (self.rect[0] / 2)
        self.bulletY = startY - (self.rect[1] / 2)
        gun_shot_sound.play()

    # def update(self,cameraX,cameraY,zombie_group):
    #     self.rect.x=self.bulletX+cameraX
    #     self.rect.y=self.bulletY+cameraY
    #     if self.rect.x>2500 or self.rect.x<-2500 or self.rect.y>2500 or self.rect.y<-2500:
    #         self.kill()
    #     # add change amount
    #     self.bulletX+=self.changeX
    #     self.bulletY+=self.changeY


    def update(self,cameraX,cameraY,zombie_group):
        if not self.kill_me:
            for i in range(int(self.continuous)):   #checks to see if bullet is touching zombie (bullet movement / bullet size) times
                self.rect.x=self.bulletX+cameraX
                self.rect.y=self.bulletY+cameraY
                self.bulletX += (14 * self.smallChangeX)
                self.bulletY += (14 * self.smallChangeY)
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
    changeX=0
    changeY=0
    grenadeX=0
    grenadeY=0
    xCounter=0
    yCounter=0
    explode=30

    def __init__(self, startX, startY, x, y):
        pygame.sprite.Sprite.__init__(self)
        angle = math.atan2(y, x)  # find angle of shot
        self.changeX = (int(50 * math.cos(angle)))  # x change amount
        self.changeY = (int(-50 * math.sin(angle)))  # Y change amount
        if self.changeX==0:
            self.changeX+=1
        if self.changeY == 0:
            self.changeY+=1
        self.image = pygame.image.load("Assets/Throwables/grenade.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.grenadeX = startX - (self.rect[0]*1.0 / 2.0) #-half of grenade size
        self.grenadeY = startY - (self.rect[1]*1.0 / 2.0)
        self.xCounter=x/self.changeX
        self.yCounter=-y/self.changeY


    def update(self, cameraX, cameraY, screen,explosions):
        #print self.xCounter, self.yCounter
        if self.explode==30:
            if self.xCounter>0:
                self.rect.x = self.grenadeX + cameraX
                self.grenadeX += self.changeX
                self.xCounter+= -1
            else:
                self.rect.x = self.grenadeX + cameraX
            if self.yCounter>0:
                self.rect.y = self.grenadeY + cameraY
                self.grenadeY += self.changeY
                self.yCounter+= -1
            else:
                self.rect.y = self.grenadeY + cameraY

            if self.xCounter<=0 and self.yCounter<=0:
                self.explode += -1
        else:
            if self.explode>0:
                self.rect.x = self.grenadeX + cameraX
                self.rect.y = self.grenadeY + cameraY
                self.explode += -1
            else:
                explosion=grenadeDetonate(self.grenadeX,self.grenadeY)
                explosions.add(explosion)
                self.kill()


class grenadeDetonate(pygame.sprite.Sprite):
    explosionX=0
    explosionY=0
    counter=1
    def __init__(self,startX,startY):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load("Assets/Effects/explosion.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.explosionX = startX - (self.rect.size[0] / 2) #-half of explosion size
        self.explosionY = startY - (self.rect.size[1] / 2)
        explosion_sound.play()

    def update(self, cameraX, cameraY):
        #times before kill
        if self.counter>0:
            self.rect.x=self.explosionX+cameraX
            self.rect.y = self.explosionY + cameraY
            self.counter+= -1
        else:
            self.kill()


class stunGrenade(pygame.sprite.Sprite):
    changeX=0
    changeY=0
    grenadeX=0
    grenadeY=0
    xCounter=0
    yCounter=0
    explode=30

    def __init__(self, startX, startY, x, y):
        pygame.sprite.Sprite.__init__(self)
        angle = math.atan2(y, x)  # find angle of shot
        self.changeX = (int(50 * math.cos(angle)))  # x change amount
        self.changeY = (int(-50 * math.sin(angle)))  # Y change amount
        if self.changeX==0:
            self.changeX+=1
        if self.changeY == 0:
            self.changeY+=1
        self.image = pygame.image.load("Assets/Throwables/stungrenade.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.grenadeX = startX - (self.rect[0]*1.0 / 2.0) #-half of grenade size
        self.grenadeY = startY - (self.rect[1]*1.0 / 2.0)
        self.xCounter=x/self.changeX
        self.yCounter=-y/self.changeY


    def update(self, cameraX, cameraY, screen,explosions):
        if self.explode==30:
            if self.xCounter>0:
                self.rect.x = self.grenadeX + cameraX
                self.grenadeX += self.changeX
                self.xCounter+= -1
            else:
                self.rect.x = self.grenadeX + cameraX
            if self.yCounter>0:
                self.rect.y = self.grenadeY + cameraY
                self.grenadeY += self.changeY
                self.yCounter+= -1
            else:
                self.rect.y = self.grenadeY + cameraY
            if self.xCounter<=0 and self.yCounter<=0:
                self.explode += -1
        else:
            if self.explode>0:
                self.rect.x = self.grenadeX + cameraX
                self.rect.y = self.grenadeY + cameraY
                self.explode += -1
            else:
                explosion=stunDetonate(self.grenadeX,self.grenadeY)
                explosions.add(explosion)
                self.kill()


class stunDetonate(pygame.sprite.Sprite):
    explosionX=0
    explosionY=0
    counter=1
    def __init__(self,startX,startY):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load("Assets/Effects/stunexplosion.png").convert_alpha()
        self.rect = self.image.get_rect()
        self.explosionX = startX - (self.rect.size[0] / 2) #-half of explosion size
        self.explosionY = startY - (self.rect.size[1] / 2)
        explosion_sound.play()

    def update(self, cameraX, cameraY):
        #times before kill
        if self.counter>0:
            self.rect.x=self.explosionX+cameraX
            self.rect.y = self.explosionY + cameraY
            self.counter+= -1
        else:
            self.kill()