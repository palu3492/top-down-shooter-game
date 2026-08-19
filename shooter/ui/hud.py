from functools import cache

import pygame

from shooter import config
from shooter.assets import load_image, load_sized
from shooter.ui.anchor import BOTTOM, RIGHT, inside, place


class Panel:
    """A piece of HUD art and the corner it stays glued to.

    The readouts drawn on a panel take their positions from its rectangle, so
    the number and the artwork it sits on can never drift apart.
    """

    def __init__(self, asset, horizontal, vertical, inset, size=None):
        self.asset = asset
        self.horizontal = horizontal
        self.vertical = vertical
        self.inset = inset
        self.size = size
        self._image = None

    @property
    def image(self):
        if self._image is None:
            self._image = (
                load_image(self.asset)
                if self.asset
                else pygame.Surface((1, 1), pygame.SRCALPHA)
            )
        return self._image

    def rect(self, window):
        return place(
            self.size or self.image.get_size(),
            window,
            self.horizontal,
            self.vertical,
            self.inset,
        )


BOTTOM_RIGHT = Panel(None, RIGHT, BOTTOM, (40, 41), (335, 157))
PANELS = (BOTTOM_RIGHT,)

HUD_TOP = 6
HUD_GAP = 12
HUD_HEIGHT = 65
CASH_SIZE = (174, HUD_HEIGHT)
HEALTH_SIZE = (334, HUD_HEIGHT)

PANEL_DARK = (35, 48, 14)
PANEL_MID = (77, 94, 31)
PANEL_EDGE = (12, 18, 4)
PANEL_SHINE = (132, 149, 57)
TRACK_DARK = (5, 25, 5)
TRACK_EDGE = (13, 45, 10)
HEALTH_DARK = (4, 145, 30)
HEART_SPRITE = "HUD/icons/heart.png"
COIN_SPRITE = "HUD/icons/coin.png"
HEART_SIZE = (42, 36)
COIN_SIZE = (42, 42)


def top_panels(window):
    """The two reference-style readouts, centred together at the top."""
    total_width = CASH_SIZE[0] + HUD_GAP + HEALTH_SIZE[0]
    left = (window[0] - total_width) // 2
    return (
        pygame.Rect(left, HUD_TOP, *CASH_SIZE),
        pygame.Rect(left + CASH_SIZE[0] + HUD_GAP, HUD_TOP, *HEALTH_SIZE),
    )


def _panel(screen, rect):
    pygame.draw.rect(screen, PANEL_EDGE, rect, border_radius=18)
    middle = rect.inflate(-5, -5)
    pygame.draw.rect(screen, PANEL_MID, middle, border_radius=16)
    pygame.draw.rect(screen, PANEL_SHINE, middle, width=2, border_radius=16)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(screen, PANEL_EDGE, inner, border_radius=13)
    pygame.draw.rect(screen, PANEL_DARK, inner.inflate(-3, -3), border_radius=11)


@cache
def _hud_text(message, size=30, colour=config.WHITE):
    """Smooth, high-contrast text for the small top-panel readouts."""
    return pygame.font.Font(None, size).render(str(message), True, colour)


@cache
def _hud_bold_text(message, size=30, colour=config.WHITE):
    font = pygame.font.Font(None, size)
    font.set_bold(True)
    return font.render(str(message), True, colour)


def _centred_text(screen, message, rect, size=30):
    text = _hud_bold_text(message, size)
    at = text.get_rect(center=rect.center)
    outline = _hud_bold_text(message, size, (35, 38, 22))
    for offset in ((-1, 0), (1, 0), (0, -1), (0, 1), (2, 2)):
        screen.blit(outline, at.move(offset))
    screen.blit(text, at)


def _icon(screen, sprite, size, centre):
    image = load_sized(sprite, *size, True)
    screen.blit(image, image.get_rect(center=centre))


class HealthBar:
    def __init__(self, window_size):
        self.window_size = window_size

    def draw(self, screen, health_update):
        _, panel = top_panels(self.window_size)
        _icon(
            screen,
            HEART_SPRITE,
            HEART_SIZE,
            (panel.left + 34, panel.centery),
        )

        track = pygame.Rect(panel.left + 60, panel.top + 14, panel.width - 77, 36)
        pygame.draw.rect(screen, TRACK_EDGE, track.inflate(4, 4), border_radius=9)
        pygame.draw.rect(screen, TRACK_DARK, track, border_radius=8)
        maximum = config.PLAYER_HEALTH
        ratio = max(0.0, min(float(health_update) / maximum, 1.0))
        fill = track.inflate(-4, -4)
        fill.width = round(fill.width * ratio)
        if fill.width:
            pygame.draw.rect(screen, HEALTH_DARK, fill, border_radius=6)
        _centred_text(
            screen,
            f"{round(health_update)} / {round(maximum)}",
            track,
            27,
        )


class HUD:
    """Corner pieces, placed when they are drawn rather than when they are made.

    `update` was already given the window; computing the offsets there means a
    resolution change moves them with no help from anyone.
    """

    def __init__(self, window=None):
        self.panels = PANELS

    def positions(self, window):
        # This reports the small anchor marker owned by HUD itself; the larger
        # weapon composition is drawn by WeaponPanel from BOTTOM_RIGHT.
        return (place((223, 121), window, RIGHT, BOTTOM, (40, 41)).topleft,)

    def update(self, screen, window):
        for panel in self.panels:
            screen.blit(panel.image, panel.rect(window))
        for panel in top_panels(window):
            _panel(screen, panel)


CLIP_READOUT = (48, 95)
RESERVE_READOUT = (116, 101)
GUN_ICON = (226, 116)
WEAPON_PICTURE_SIZE = (114, 95)

THROWABLE_SIZE = (86, 78)
THROWABLE_GAP = 7
ACTIVE_DIAMETER = 148
AMMO_SIZE = (177, 76)
AMMO_ICON_SPRITE = "HUD/icons/bullet.png"
AMMO_ICON_SIZE = (34, 40)


def _outlined_text(message, size, colour=config.WHITE):
    """Real rendered text with the heavy dark edge used by the reference."""
    font = pygame.font.Font(None, size)
    face = font.render(str(message), True, colour)
    outline = font.render(str(message), True, (12, 15, 7))
    canvas = pygame.Surface(
        (face.get_width() + 4, face.get_height() + 4), pygame.SRCALPHA
    )
    for dx, dy in ((0, 2), (4, 2), (2, 0), (2, 4)):
        canvas.blit(outline, (dx, dy))
    canvas.blit(face, (2, 2))
    return canvas


def _hud_box(screen, rect, radius=16):
    """Layered olive panel, closely matching the supplied HUD reference."""
    pygame.draw.rect(screen, (8, 12, 4), rect, border_radius=radius)
    pygame.draw.rect(
        screen, (91, 106, 47), rect.inflate(-5, -5), border_radius=max(3, radius - 3)
    )
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(screen, (35, 48, 20), inner, border_radius=max(3, radius - 6))


def _throwable_box(screen, rect):
    """Compact olive inventory tile used by both throwable counters."""
    pygame.draw.rect(screen, (7, 12, 3), rect, border_radius=13)
    rim = rect.inflate(-4, -4)
    pygame.draw.rect(screen, (81, 105, 27), rim, border_radius=11)
    inner = rect.inflate(-8, -8)
    pygame.draw.rect(screen, (38, 53, 18), inner, border_radius=9)
    pygame.draw.line(
        screen,
        (65, 81, 27),
        (inner.left + 2, inner.top + 9),
        (inner.left + 2, inner.bottom - 9),
        2,
    )


def weapon_hud_rects(window):
    """Reference-style layout anchored as one unit to the bottom-right."""
    whole = BOTTOM_RIGHT.rect(window)
    active = pygame.Rect(
        whole.right - ACTIVE_DIAMETER, whole.top + 9, ACTIVE_DIAMETER, ACTIVE_DIAMETER
    )
    ammo = pygame.Rect(whole.left, whole.bottom - AMMO_SIZE[1], *AMMO_SIZE)
    stun = pygame.Rect(
        ammo.left + THROWABLE_SIZE[0] + THROWABLE_GAP,
        ammo.top - THROWABLE_SIZE[1] - THROWABLE_GAP,
        *THROWABLE_SIZE,
    )
    grenade = pygame.Rect(ammo.left, stun.top, *THROWABLE_SIZE)
    return grenade, stun, ammo, active


class WeaponPanel:
    """The bottom-right readout: what is loaded, what is left, and what is held.

    It holds no ammunition of its own -- it is handed whatever is equipped and
    reports that, so both the numbers and the picture follow the weapon rather
    than being the one gun that existed when this was written.
    """

    def __init__(self, window, grenades=None):
        self.window = window
        self.grenades = grenades

    def draw(self, screen, held):
        grenade, stun, ammo, active = weapon_hud_rects(self.window)
        self._throwable(
            screen,
            grenade,
            "HUD/throwables/grenade-hud.png",
            self.grenades.grenade_amount if self.grenades else 0,
        )
        self._throwable(
            screen,
            stun,
            "HUD/throwables/stun-grenade-hud.png",
            self.grenades.stun_grenade_amount if self.grenades else 0,
        )

        pygame.draw.circle(screen, (8, 12, 4), active.center, active.width // 2)
        pygame.draw.circle(screen, (91, 106, 47), active.center, active.width // 2 - 4)
        pygame.draw.circle(screen, (35, 48, 20), active.center, active.width // 2 - 9)

        picture = self._picture(held.weapon, WEAPON_PICTURE_SIZE)
        picture_at = picture.get_rect(center=active.center)
        screen.blit(picture, picture_at)

        loaded = 0 if held.loaded is None else held.loaded
        reserve = 0 if held.reserve is None else held.reserve
        _hud_box(screen, ammo, 16)
        _icon(
            screen,
            AMMO_ICON_SPRITE,
            AMMO_ICON_SIZE,
            (ammo.left + 25, ammo.centery - 2),
        )
        screen.blit(
            pygame.font.Font(None, 55).render(str(loaded), True, config.WHITE),
            inside(BOTTOM_RIGHT.rect(self.window), CLIP_READOUT),
        )
        slash = _outlined_text("/", 43)
        screen.blit(slash, (ammo.left + 91, ammo.top + 22))
        screen.blit(
            pygame.font.Font(None, 44).render(str(reserve), True, config.WHITE),
            inside(BOTTOM_RIGHT.rect(self.window), RESERVE_READOUT),
        )

    def _throwable(self, screen, rect, sprite, count):
        _throwable_box(screen, rect)
        icon = load_sized(sprite, 58, 58, True)
        screen.blit(icon, icon.get_rect(center=(rect.centerx + 7, rect.centery + 5)))

        # Match the reference's single, prominent quantity badge.
        amount = _outlined_text(count, 27)
        screen.blit(amount, (rect.left + 8, rect.top + 5))

    def _picture(self, weapon, bounds=WEAPON_PICTURE_SIZE):
        """Fit the weapon art within the active-weapon circle."""
        if weapon.sprite is None:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        image = load_image(weapon.sprite)
        scale = min(1.0, bounds[0] / image.get_width(), bounds[1] / image.get_height())
        if scale == 1.0:
            return image
        size = (
            max(1, round(image.get_width() * scale)),
            max(1, round(image.get_height() * scale)),
        )
        return pygame.transform.smoothscale(image, size)


class GrenadeData:
    def __init__(self):
        self.grenade_amount = config.STARTING_GRENADES
        self.stun_grenade_amount = config.STARTING_STUN_GRENADES


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
        panel, _ = top_panels(window)
        _icon(
            screen,
            COIN_SPRITE,
            COIN_SIZE,
            (panel.left + 36, panel.centery),
        )
        readout = pygame.Rect(
            panel.left + 65, panel.top, panel.width - 72, panel.height
        )
        _centred_text(screen, self.cash_amount, readout, 34)


# Under the player rather than at a fixed height near the top, where the
# between-wave banner already is -- the two were printing over each other.
PROMPT_BELOW = 90


def prompt(screen, window, label):
    """What standing next to something says before you press anything.

    Not in `shopfront`, where it started: a tree offers itself the same way the
    gun stand does, and only one of them is a shop.
    """
    text = pygame.font.Font(None, 30).render(f"[E]  {label}", True, config.WHITE)
    screen.blit(
        text,
        (window[0] / 2 - text.get_width() / 2, window[1] / 2 + PROMPT_BELOW),
    )
