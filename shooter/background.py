import pygame

from shooter.assets import load_sheet


class BackgroundSheet:
    """A window onto one large image.

    The sheet is shared rather than owned: `image_at` only ever reads from it,
    so every session can sample the same surface instead of each paying 180ms
    to load its own copy.
    """

    def __init__(self, relative):
        self.sheet = load_sheet(relative)

    def image_at(self, rectangle, colorkey=None):
        "Loads image from x,y,x+offset,y+offset"
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size).convert()
        image.blit(self.sheet, (0, 0), rect)
        if colorkey is not None:
            if colorkey == -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image
