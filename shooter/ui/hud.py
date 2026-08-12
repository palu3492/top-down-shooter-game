import pygame

from shooter import config
from shooter.assets import load_image
from shooter.ui.anchor import BOTTOM, CENTRE, LEFT, RIGHT, TOP, inside, place


class Panel:
    """A piece of HUD art and the corner it stays glued to.

    The readouts drawn on a panel take their positions from its rectangle, so
    the number and the artwork it sits on can never drift apart.
    """

    def __init__(self, asset, horizontal, vertical, inset):
        self.asset = asset
        self.horizontal = horizontal
        self.vertical = vertical
        self.inset = inset
        self._image = None

    @property
    def image(self):
        if self._image is None:
            self._image = load_image(self.asset)
        return self._image

    def rect(self, window):
        return place(
            self.image.get_size(), window, self.horizontal, self.vertical, self.inset
        )


BOTTOM_LEFT = Panel("HUD/blHUD.png", LEFT, BOTTOM, (40, 30))
BOTTOM_RIGHT = Panel("HUD/brHUD.png", RIGHT, BOTTOM, (40, 41))
TOP_MIDDLE = Panel("HUD/tmHUD.png", CENTRE, TOP, (0, 0))
PANELS = (BOTTOM_LEFT, BOTTOM_RIGHT, TOP_MIDDLE)


HEALTH_READOUT = (30, -1)
HEALTH_METER = (165, 10)
METER_SIZE = (100 * 2.2, 22)


class HealthBar:
    def __init__(self, window_size):
        self.window_size = window_size

    def draw(self, screen, health_update):
        readout = BOTTOM_LEFT.rect(self.window_size)
        screen.blit(
            pygame.font.Font(None, 55).render(str(health_update), True, config.WHITE),
            inside(readout, HEALTH_READOUT),
        )

        meter = TOP_MIDDLE.rect(self.window_size)
        left, top = inside(meter, HEALTH_METER)
        pygame.draw.rect(
            screen, config.HEALTH_GREEN, (left, top, health_update * 2.2, METER_SIZE[1])
        )
        pygame.draw.rect(screen, config.HEALTH_GREY, (left, top, *METER_SIZE), 4)


class HUD:
    """Corner pieces, placed when they are drawn rather than when they are made.

    `update` was already given the window; computing the offsets there means a
    resolution change moves them with no help from anyone.
    """

    def __init__(self, window=None):
        self.panels = PANELS

    def positions(self, window):
        return tuple(panel.rect(window).topleft for panel in self.panels)

    def update(self, screen, window):
        for panel in self.panels:
            screen.blit(panel.image, panel.rect(window))


CLIP_READOUT = (13, 57)
RESERVE_READOUT = (93, 60)
GUN_ICON = (138, 42)


class GunData:
    CLIP = config.CLIP_SIZE
    RESERVE = config.RESERVE_SIZE

    def __init__(self, window):
        self.window = window
        self.clip_size = self.CLIP
        self.ammo_amount = self.RESERVE
        self.reload_seconds = config.RELOAD_SECONDS
        self.gun_type = load_image("HUD/gunShotty.png")

    def shooting_bullet(self):
        if self.clip_size > 1:
            self.clip_size -= 1
        elif self.clip_size == 1:
            self.clip_size -= 1
            if self.ammo_amount > 0:
                return self.reload_ammo()
        else:
            return "no ammo"

    def reload_ammo(self):
        # if clip is empty and ammo has at least 60 bullets
        if self.ammo_amount >= 60 and self.clip_size == 0:
            self.ammo_amount -= 60
            self.clip_size = 60
        # if clip is empty and ammo does not have 60 bullets in it
        elif self.ammo_amount < 60 and self.clip_size == 0:
            self.clip_size = self.ammo_amount
            self.ammo_amount = 0
        # if clip has bullets in it and ammo has enough to fill it
        elif self.clip_size != 0 and self.ammo_amount >= 60 - self.clip_size:
            self.ammo_amount -= 60 - self.clip_size
            self.clip_size = 60
        # if clip has bullets in it and ammo cant fill it
        elif self.clip_size != 0 and self.ammo_amount < 60 - self.clip_size:
            self.clip_size += self.ammo_amount
            self.ammo_amount = 0
        return "reload"

    def refill(self):
        self.ammo_amount = self.RESERVE

    def manual_reload(self):
        if self.ammo_amount > 0:
            return self.reload_ammo()
        elif self.clip_size == 0:
            return "no ammo"

    def reloading(self, dt=config.SIM_DT):
        if self.reload_seconds > 0:
            self.reload_seconds -= dt
            return "reload"
        self.reload_seconds = config.RELOAD_SECONDS
        return None

    def update(self, screen):
        panel = BOTTOM_RIGHT.rect(self.window)
        screen.blit(
            pygame.font.Font(None, 55).render(str(self.clip_size), True, config.WHITE),
            inside(panel, CLIP_READOUT),
        )
        screen.blit(
            pygame.font.Font(None, 44).render(
                str(self.ammo_amount), True, config.WHITE
            ),
            inside(panel, RESERVE_READOUT),
        )
        screen.blit(self.gun_type, inside(panel, GUN_ICON))


class GrenadeData:
    def __init__(self):
        self.grenade_amount = config.STARTING_GRENADES
        self.stun_grenade_amount = config.STARTING_STUN_GRENADES


CASH_READOUT = (85, 7)


class Cash:
    def __init__(self):
        self.cash_amount = 0

    # Method used when zombie dies
    def increase_cash(self, amount):
        self.cash_amount += amount

    # Method controls players cash
    # if player has the cash to purchase Item method will
    # return True allowing the purchase to be made
    def cash_add_remove(self, cash):
        if self.cash_amount + cash < 0:
            return False
        self.cash_amount += cash
        return True

    def update(self, screen, window):
        screen.blit(
            pygame.font.Font(None, 40).render(
                "$" + str(self.cash_amount), True, config.WHITE
            ),
            inside(TOP_MIDDLE.rect(window), CASH_READOUT),
        )
