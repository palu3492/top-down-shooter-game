import pygame

class RadarScrn:

    def __init__(self):
        pass

    def draw(self, screen, X, Y):
        pygame.draw.rect(screen, (200, 200, 200), (10, 10, 100, 100))
        pygame.draw.line(screen, (0, 0, 0), (10, 60), (110,60))
        pygame.draw.line(screen, (0, 0, 0), (60, 10), (60, 110))
        pygame.draw.rect(screen, (60, 255, 60), (10+int(X/50), 10+int(Y/50), 5, 5))

    def update_zom(self, screen, zombie):
        X,Y = zombie.get_posistion()
        pygame.draw.rect(screen, (255, 60, 60), (10+int(X/50), 10+int(Y/50), 5, 5))
