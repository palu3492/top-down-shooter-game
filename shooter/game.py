import pygame
import math

from shooter.assets import asset_path, load_image
from shooter.entities.player import Human
from shooter.systems.waves import  Wave_System
#from CarePackage import PackageSystem
from shooter.ui.hud import *
from shooter.ui.radar import *
from shooter.background import loadBackground
from shooter.entities.projectiles import *
from shooter.entities.powerups import PowerUps

def reset_zombie_pos(zombie):
    zombie.reset_posistion()

def is_zombie_attacking(human, zombie):
    pygame.sprite.collide_rect_ratio(.5)
    if pygame.sprite.collide_rect(human, zombie):
        #zombie.update_anim("ATTACK")
        if human.remove_health(.10): #if return True (player is dead) then change to idle and kill player
            #zombie.update_anim("IDLE")
            human.kill()

def explosion_touching_zombie(zombie, explotion):
    if pygame.sprite.collide_rect(zombie, explotion):
        if zombie.remove_health(75):
            zombie.kill()

def stun_explosion_touching_zombie(zombie, explotion):
    if pygame.sprite.collide_rect(zombie, explotion):
        zombie.remove_speed(3)

def game_loop():
    pygame.init()
    window = (1080, 720)
    screen = pygame.display.set_mode(window)
    screen.blit(pygame.font.Font(None, 40).render("Loading...", True, (255, 255, 255)), (100, 100))
    pygame.display.update()
    game_is_running = True
    fullscreen_flag = True

    cursor = load_image('cursor.png')
    pygame.mouse.set_visible(False)

    cameraX, cameraY = 0,0

    bck = loadBackground(asset_path("Backgrounds/background_0.jpg"))

    heads_up_display=HUD(window)
    human = Human(window)
    radar = RadarScrn()
    player_cash = Cash()
    health_data = HealthBar(window)
    bullets = pygame.sprite.Group()
    grenades = pygame.sprite.Group()
    explosions=pygame.sprite.Group()
    stun_grenades=pygame.sprite.Group()
    stun_explosions=pygame.sprite.Group()
    all_grenade_data=grenade_data()
    human_group = pygame.sprite.Group(human)
    zombie_group = pygame.sprite.Group()
    powerups_group = pygame.sprite.Group()
    powerups_group.add(PowerUps())

    wave_system = Wave_System(window, zombie_group, player_cash)

    mouseX = pygame.mouse.get_pos()[0]
    mouseY = pygame.mouse.get_pos()[1]
    centerX = int(mouseX - (window[0] / 2.0))
    centerY = -int(mouseY - (window[1] / 2.0))

    ammo_class=gun_data(window)
    ammoCount=""

    clock = pygame.time.Clock()
    while game_is_running:
        changeX=changeY=0
        human_anim = "MOVE"

        #Fullscreen Switch
        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_BACKSLASH]:
            if fullscreen_flag:
                screen = pygame.display.set_mode(window)
                fullscreen_flag = False
            else:
                screen = pygame.display.set_mode(window, pygame.FULLSCREEN)
                fullscreen_flag = True

        #Controls for moving the camera, moving 40 px per frame
        if human.alive():
            if pressed[pygame.K_w]:
                changeY = 10
            elif pressed[pygame.K_s]:
                changeY = -10
            if pressed[pygame.K_a]:
                changeX = 10
            elif pressed[pygame.K_d]:
                changeX = -10

        cameraX += changeX
        cameraY += changeY

        if cameraX>0:
            cameraX=0
        elif cameraX < -5000+window[0]:
            cameraX=-5000+window[0]
        if cameraY>0:
            cameraY=0
        elif cameraY<-5000+window[1]:
            cameraY=-5000+window[1]

        #When button is lifted up sets camera x,y change to 0
        if changeX<=0 or changeY<=0:
            human_anim = "IDLE"

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if ammoCount!="no ammo" and ammoCount!="reload":
                    human_anim = "SHOOT"
                    bullet = Shot((window[0]/2.0)-cameraX, (window[1]/2.0)-cameraY, centerX, centerY)
                    bullets.add(bullet)
                    ammoCount = ammo_class.shooting_bullet()
            if event.type==pygame.QUIT:
                game_is_running = False
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_g:
                    if all_grenade_data.grenade_amount > 0:
                        grenade = Grenade((window[0] / 2.0) - cameraX, (window[1] / 2.0) - cameraY, centerX, centerY)
                        grenades.add(grenade)
                        all_grenade_data.grenade_amount -= 1
                if event.key==pygame.K_f:
                    if all_grenade_data.stun_grenade_amount>0:
                        stun_grenade = stunGrenade((window[0] / 2.0) - cameraX, (window[1] / 2.0) - cameraY, centerX, centerY)
                        stun_grenades.add(stun_grenade)
                        all_grenade_data.stun_grenade_amount-=1
                if event.key == pygame.K_r:
                    ammoCount = ammo_class.manual_reload()

        if ammoCount=="reload":
            ammoCount=ammo_class.reloading(screen)

        # Quit the game
        if pressed[pygame.K_p]:
            game_is_running = False

        #Human
        if human_anim == "IDLE":
            human.update_anim("IDLE")
        elif human_anim == "MOVE":
            human.update_anim("MOVE")
        elif human_anim == "SHOOT":
            human.update_anim("SHOOT")


        #Controls background rendering
        image = bck.image_at((0 - cameraX, 0 - cameraY, window[0], window[1]))
        screen.blit(image, (0, 0))

        # 1. Updates zombie animation
        # 1. Checks if Zombie is attacking
        # 2. Sends zombie to Human
        # 3. Moves Zombies when camera moves
        for zombie in zombie_group:
            #zombie.update_anim("MOVE")
            is_zombie_attacking(human, zombie)
            zombie.moveZombieTowardMid(cameraX,cameraY)
            zombie.health_bar(screen)
            for explosion in explosions:
                explosion_touching_zombie(zombie, explosion)
            for stun_explosion in stun_explosions:
                stun_explosion_touching_zombie(zombie, stun_explosion)
            zombie.zombie_speed_timer() #check to see if zombie is stunnded and deduct time from stun time



        #Mouse Controls
        mouseX = pygame.mouse.get_pos()[0]
        mouseY = pygame.mouse.get_pos()[1]
        centerX = int(mouseX - (window[0] / 2))
        centerY = -int(mouseY - (window[1] / 2))
        rotationAngle = math.degrees(math.atan2(centerY, centerX))
        human.rot_center(rotationAngle)

        ###################################
        #
        #           Updates PowerUps
        #           Draws to screen
        #
        ###################################
        for powerup in powerups_group:
            if powerup.update(human, zombie_group, screen, changeX,changeY):
                powerup.kill()
        powerups_group.draw(screen)

        #Loads in Human and Zombie
        zombie_group.draw(screen)
        human_group.draw(screen)

        #Bullet animation
        bullets.update(cameraX, cameraY,zombie_group)
        bullets.draw(screen)

        if len(zombie_group) == 0:
            controls_on = False
            if wave_system.wave_gui(screen):
                wave_system.wave_control(screen, window, zombie_group, player_cash)

        #Grenades and explosions
        grenades.update(cameraX, cameraY, screen, explosions)
        grenades.draw(screen)
        explosions.update(cameraX, cameraY)
        explosions.draw(screen)
        stun_grenades.update(cameraX, cameraY, screen, stun_explosions)
        stun_grenades.draw(screen)
        stun_explosions.update(cameraX, cameraY)
        stun_explosions.draw(screen)

        #Draw crosshair cursor
        screen.blit(cursor, (mouseX - 23, mouseY - 22))

        #pygame.draw.rect(screen, (255, 255, 255), human.get_rect())

        # Updating radar with new data, Human and Zombies
        radar.draw(screen, -cameraX+960, -cameraY+540)
        for zombie in zombie_group:
            radar.update_zom(screen, zombie)

        heads_up_display.update(screen,window)
        #Updates Health Bar
        health_data.draw(screen, human.get_health())
        ammo_class.update(screen)
        player_cash.update(screen)

        if ammoCount == "reload":
            screen.blit(pygame.font.Font(None, 30).render("Reloading", True, (255, 255, 255)), ((window[0]/2.0)-50, 100))

        screen.blit(pygame.font.Font(None, 20).render(str(clock.get_fps()), True, (255, 255, 255)), (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
