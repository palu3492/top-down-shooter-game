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
from shooter.assets import load_animation, load_image, load_scaled, load_sized
from shooter.entities import player, zombie

SPRITES = (
    ("cursor.png", False),
    ("HUD/brHUD.png", False),
    ("HUD/gunAK47.png", False),
    ("HUD/gunShotty.png", False),
    ("HUD/gunSMG.png", False),
    ("HUD/gunSniper.png", False),
    ("HUD/knife.png", False),
    ("HUD/icons/coin.png", True),
    ("HUD/icons/heart.png", True),
    ("HUD/throwables/grenade-hud.png", True),
    ("HUD/throwables/stun-grenade-hud.png", True),
    ("Props/gun_stand.png", True),
    ("Props/tree.png", True),
    ("Props/tree_damaged.png", True),
    ("Props/tree_critical.png", True),
    ("Props/rock.png", True),
    ("Props/rock_damaged.png", True),
    ("Props/rock_critical.png", True),
    ("Props/rock_ruined.png", True),
    ("Pickups/log.png", True),
    ("Pickups/rock.png", True),
    ("Pickups/cloth.png", True),
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

BACKGROUND_TILE = "Backgrounds/grass_tile.png"
MENU_ART = "Backgrounds/menu_pixel.png"

ZOMBIE_STILL = "Zombie Animations/zombie_idle/skeleton-idle_0.png"


def preload():
    """Warm every cache a session reads from. Safe to call more than once."""
    for relative, alpha in SPRITES:
        load_image(relative, alpha)

    load_scaled("Props/tree_damaged.png", 1.15, True)
    load_scaled("Props/tree_critical.png", 1.15, True)
    load_scaled("Props/rock_damaged.png", 1.30, True)
    load_scaled("Props/rock_critical.png", 1.30, True)
    load_scaled("Props/rock_ruined.png", 1.30, True)

    load_image(MENU_ART)
    load_image(BACKGROUND_TILE)

    for animations in player.ANIMATIONS.values():
        for directory, prefix, count in animations.values():
            load_animation(directory, prefix, count, config.PLAYER_SCALE, True)

    for name, (directory, prefix, count) in zombie.ANIMATIONS.items():
        load_animation(
            directory,
            prefix,
            count,
            config.ZOMBIE_SCALE * zombie.ANIMATION_SCALE[name],
            True,
        )

    load_sized(ZOMBIE_STILL, *config.ZOMBIE_SIZE, True)
