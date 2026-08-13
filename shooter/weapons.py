"""What a gun is, apart from the corner of the screen that draws one.

This lived in `ui/hud.py`, which is where it was put when there was one gun and
it was mostly a readout. A weapon model inside the HUD cannot grow: the SMG, the
sniper and the crossbow are all differences in numbers, and numbers belong in a
table rather than in a class per gun.

The one gun is a semi-automatic rifle and always has been -- every frame of the
player is `survivor-*_rifle_*`, it fires one bullet per click with no spread,
and it holds sixty rounds. Only the HUD icon ever called it a shotgun.

So a weapon is split the way AT37 split everything else. The `Item` is its
identity -- what the backpack carries, what the shop sells, what a slot shows.
The `Weapon` is what it *does*, and one is built for each `Gun` that exists.
"""

from dataclasses import dataclass

from shooter import config, items

NO_AMMO = "no ammo"
RELOAD = "reload"


class UnknownWeaponError(KeyError):
    """A weapon id nothing has been registered under."""


@dataclass(frozen=True)
class Weapon:
    """The numbers that make one gun different from another.

    `clip` is how many rounds it holds; `reserve` is how many it comes with
    outside the clip. A `Gun` starts full of both.
    """

    item: items.Item
    ammo: items.Item
    sprite: str
    clip: int
    reserve: int
    damage: int
    reload_seconds: float

    @property
    def id(self):
        return self.item.id

    @property
    def name(self):
        return self.item.name


BUILDERS = {}


def register(item, build):
    """Declare a weapon: its identity, and how to build its stats."""
    BUILDERS[item.id] = build
    return item


def weapon(weapon_id):
    """Built when it is asked for rather than once at import.

    `RELOAD_SECONDS` is a setting the player can change, and AT23's guard
    refuses import-bound copies of those for a good reason -- a table of
    finished weapons would go on reporting the value it read when the module
    loaded, and the settings screen would appear to do nothing.
    """
    if weapon_id not in BUILDERS:
        raise UnknownWeaponError(weapon_id)
    return BUILDERS[weapon_id]()


def weapon_ids():
    return tuple(BUILDERS)


RIFLE_ROUNDS = items.register(items.Item("556", "5.56mm", items.AMMO, stack=50))
M16 = items.register(items.Item("m16", "M16", items.WEAPON))

register(
    M16,
    lambda: Weapon(
        item=M16,
        ammo=RIFLE_ROUNDS,
        sprite="HUD/gunAK47.png",
        clip=config.CLIP_SIZE,
        reserve=config.RESERVE_SIZE,
        damage=config.BULLET_DAMAGE,
        reload_seconds=config.RELOAD_SECONDS,
    ),
)


class Gun:
    """A weapon, and what is currently in it.

    `loaded` is what the clip holds now; `weapon.clip` is what it holds when
    full. Keeping the two apart is the whole reason the literal `60` could be
    written eleven times without anyone noticing it was the same number.
    """

    def __init__(self, which=M16):
        self.weapon = which if isinstance(which, Weapon) else weapon(_id_of(which))
        self.loaded = self.weapon.clip
        self.reserve = self.weapon.reserve
        self.reload_seconds = self.weapon.reload_seconds

    @property
    def damage(self):
        return self.weapon.damage

    def fire(self):
        """Spend a round. Emptying the clip starts a reload if there is one."""
        if self.loaded > 1:
            self.loaded -= 1
            return None
        if self.loaded == 1:
            self.loaded = 0
            return self.reload() if self.reserve > 0 else None
        return NO_AMMO

    def reload(self):
        """Move as much of the reserve into the clip as will go.

        Four branches asking whether the clip was empty and whether the reserve
        could fill it, each with `60` written into it, say exactly this. Nothing
        loads a clip past its size, so there is no negative case to guard.
        """
        taken = min(self.weapon.clip - self.loaded, self.reserve)
        self.loaded += taken
        self.reserve -= taken
        return RELOAD

    def manual_reload(self):
        if self.reserve > 0:
            return self.reload()
        return NO_AMMO if self.loaded == 0 else None

    def refill(self):
        self.reserve = self.weapon.reserve

    def reloading(self, dt=config.SIM_DT):
        """Count down the reload, and report when it is still running."""
        if self.reload_seconds > 0:
            self.reload_seconds -= dt
            return RELOAD
        self.reload_seconds = self.weapon.reload_seconds
        return None


def _id_of(which):
    return which.id if isinstance(which, items.Item) else which
