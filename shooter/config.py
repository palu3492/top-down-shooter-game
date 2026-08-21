"""Tunable values for the game.

Speeds are pixels per second and durations are seconds, so behaviour is
identical whatever frame rate the loop actually achieves.
"""

# Rendering and simulation are independent: frames interpolate between steps.
# The cap sits above common refresh rates rather than uncapped, which would spin
# a core; vsync is a display concern and belongs with AT17.
FPS = 240
SIM_HZ = 60
SIM_DT = 1 / SIM_HZ

DEV_TOOLS = True

WINDOW = (1080, 720)  # the logical render size; SCALED stretches it to the window
VSYNC = True  # set_mode takes a bool here, so the setting is a switch
# The shipped world is 10,000px square. Session movement reads the authoritative
# size from the loaded TMX; this shared value remains for systems such as radar
# that do not own the map.
WORLD = (10000, 10000)

PLAYER_SPEED = 600
PLAYER_HEALTH = 100.0
PLAYER_REGEN = 3.0
PLAYER_SCALE = 0.5

ZOMBIE_SPEED = 360
ZOMBIE_HEALTH = 100.0
ZOMBIE_DAMAGE = 6.0
ZOMBIE_SIZE = (120, 111)
ZOMBIE_SCALE = 0.5
KILL_REWARD = 50

# Temporary gameplay switch. Set this back to True to restore wave spawning.
ZOMBIE_SPAWNING_ENABLED = False

# A wave starts this many seconds of travel outside the view, so the player
# sees it coming instead of meeting it at the edge of the screen.
SPAWN_LEAD_SECONDS = 3.0

BULLET_SPEED = 9000
BULLET_STEP = 14  # max pixels between collision checks
EXPLOSION_SECONDS = 1 / 60
ANIMATION_FPS = 60
ZOMBIE_ANIMATION_FPS = 18
MAX_FRAME_SECONDS = 0.1  # clamp: a stalled frame must not teleport anything
BULLET_DAMAGE = 20
BULLET_RANGE = 1000
LETHAL = 1000

GRENADE_SPEED = 3000
GRENADE_FUSE = 0.5
EXPLOSION_DAMAGE = 75
STUN_SPEED = 180
STUN_SECONDS = 200 / 60

# The knife: two hits to put a zombie down, but only from close enough that
# missing means being hit back. Reach is measured from the player's centre to
# the zombie's, so it is a little shorter than it reads.
KNIFE_DAMAGE = 50
KNIFE_RATE = 2.5
KNIFE_REACH = 140
KNIFE_ARC = 100

CLIP_SIZE = 60
RESERVE_SIZE = 120
RELOAD_SECONDS = 1.0
STARTING_GRENADES = 5
STARTING_STUN_GRENADES = 5

WAVE_BASE = 5
WAVE_INTERVAL_SECONDS = 25.0

POWERUP_LIFETIME_SECONDS = 20.0
POWERUP_BLINK_AFTER = 400 / 60
# The original frame windows, converted; the pickup flashes faster as it ages.
POWERUP_BLINK_WINDOWS = tuple(
    (start / 60, end / 60)
    for start, end in (
        (400, 500),
        (600, 650),
        (800, 850),
        (1000, 1050),
        (1100, 1125),
        (1150, 1175),
    )
)
POWERUP_SPAWN = (800, 500)
INSTAKILL_SECONDS = 30.0

RADAR_ORIGIN = (10, 10)
RADAR_SIZE = 100
RADAR_SCALE = WORLD[0] // RADAR_SIZE
RADAR_BLIP = 5

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
HEALTH_GREEN = (66, 255, 66)
HEALTH_RED = (244, 66, 66)
HEALTH_GREY = (96, 96, 96)
RADAR_BACKGROUND = (200, 200, 200)
RADAR_PLAYER = (60, 255, 60)
RADAR_ZOMBIE = (255, 60, 60)
INSTAKILL_TEXT = (255, 80, 80)
