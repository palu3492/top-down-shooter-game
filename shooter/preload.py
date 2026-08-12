"""Reading every asset before play, so nothing reads one during it.

Loading is lazy and cached, which is the right default and the wrong thing to
discover mid-frame. Two costs were measured before this existed: the world
background is 5000x5000 and took 180ms *per session* because it bypassed the
cache entirely, and eight sprites -- the HUD panels, projectiles and effects --
were first read while the player was already moving.

The manifest is deliberately explicit rather than a walk of the assets
directory: 14MB of the 19MB on disk is backgrounds this mode never shows, and
loading them would trade a hitch for a slower start. `tests/test_preload.py` is
what keeps the list honest -- it fails if anything reaches disk during play.
"""

from shooter import config
from shooter.assets import load_animation, load_image, load_sheet, load_sized
from shooter.entities import player, zombie

SPRITES = (
    ("cursor.png", False),
    ("HUD/blHUD.png", False),
    ("HUD/brHUD.png", False),
    ("HUD/tmHUD.png", False),
    ("HUD/gunShotty.png", False),
    ("Power Ups/instakill.png", False),
    ("Power Ups/Nuke.png", False),
    ("Power Ups/MaxAmmo.png", False),
    ("Power Ups/MaxHealth.png", False),
    ("Projectiles/bullet.png", True),
    ("Throwables/grenade.png", True),
    ("Throwables/stungrenade.png", True),
    ("Effects/explosion.png", True),
    ("Effects/stunexplosion.png", True),
)

SHEETS = ("Backgrounds/background_0.jpg",)
MENU_ART = "Backgrounds/menu_1.jpg"

ZOMBIE_STILL = "Zombie Animations/zombie_idle/skeleton-idle_0.png"


def preload():
    """Warm every cache a session reads from. Safe to call more than once."""
    for relative, alpha in SPRITES:
        load_image(relative, alpha)

    load_image(MENU_ART)

    for relative in SHEETS:
        load_sheet(relative)

    for directory, prefix, count in player.ANIMATIONS.values():
        load_animation(directory, prefix, count, config.PLAYER_SCALE)

    for directory, prefix, count in zombie.ANIMATIONS.values():
        load_animation(directory, prefix, count, config.ZOMBIE_SCALE, True)

    load_sized(ZOMBIE_STILL, *config.ZOMBIE_SIZE, True)
