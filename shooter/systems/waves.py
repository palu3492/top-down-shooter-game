from shooter.entities.zombie import *
from shooter.ui.hud import *
import pygame

class Wave_System:

    Wave_Count = 0
    Wave_Timer = 0

    def __init__(self, window, zombie_group, player_cash):
        for _ in range(5):
            zombie_group.add(Zombie(window, player_cash))

    def wave_gui(self, screen):
        return True

    def wave_control(self, screen, window, zombie_group, player_cash):
        #Timer and next wave spawner
        if self.Wave_Timer == 1500:
            self.Wave_Count += 1
            num_spawn = 5 + (pow(self.Wave_Count, 2))
            for _ in range(num_spawn):
                zombie_group.add(Zombie(window, player_cash))
            self.Wave_Timer = 0
        else:
            self.Wave_Timer += 1

        # Updating timer to screen
        screen.blit(pygame.font.Font(None, 40).render("Time until next round " + str(15-(int(self.Wave_Timer/100))), True, (255, 255, 255)), (400, 150))
        screen.blit(pygame.font.Font(None, 40).render("or press [SPACE] to continue" , True, (255, 255, 255)), (370, 180))

        pygame.draw.rect(screen,(100, 100, 100), (300, 210, 500, 100))
        pygame.draw.rect(screen,(100, 255, 100), (300, 210, 500, 10))
        screen.blit(pygame.font.Font(None, 40).render("   [AMMO]        [HEALTH]        [GUN]" , True, (255, 255, 255)), (300, 230))

        # Checks if player is pressing SPACE
        # if so, then timer is set to 0 and
        # next round starts
        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_SPACE]:
            self.Wave_Timer = 1500
