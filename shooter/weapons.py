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
from shooter.entities.projectiles import Shot, Swing

NO_AMMO = "no ammo"
RELOAD = "reload"


class UnknownWeaponError(KeyError):
    """A weapon id nothing has been registered under."""


@dataclass(frozen=True)
class Melee:
    """A blade. It has no ammunition and no reload, which is the point.

    `reach` is how far it can touch and `arc` how wide a wedge in front of the
    player it sweeps, in degrees.
    """

    item: items.Item
    sprite: str | None
    damage: int
    reach: int
    arc: float

    @property
    def id(self):
        return self.item.id

    @property
    def name(self):
        return self.item.name


@dataclass(frozen=True)
class Weapon:
    """The numbers that make one gun different from another.

    `clip` is how many rounds it holds; `reserve` is how many it comes with
    outside the clip. A `Gun` starts full of both.
    """

    item: items.Item
    ammo: items.Item
    sprite: str | None
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


KNIFE = items.register(items.Item("knife", "Knife", items.TOOL))

register(
    KNIFE,
    # No knife art exists, so the readout falls back to the name. AT40 owns it.
    lambda: Melee(
        item=KNIFE,
        sprite=None,
        damage=config.KNIFE_DAMAGE,
        reach=config.KNIFE_REACH,
        arc=config.KNIFE_ARC,
    ),
)

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


SLOTS = (KNIFE.id, M16.id)


def equip(which):
    """Build whatever holds this weapon: a blade for a blade, a gun for a gun.

    Keys `1`-`5` and the armoury both need one call that does not care which
    kind it is asking for.
    """
    made = which if isinstance(which, (Melee, Weapon)) else weapon(_id_of(which))
    return Blade(made) if isinstance(made, Melee) else Gun(made)


class Blade:
    """A knife in the hand. Nothing to load, so nothing to run out of.

    `loaded` and `reserve` are `None` rather than zero: a knife does not have
    an empty magazine, it has no magazine, and the readout has to be able to
    tell those apart.
    """

    def __init__(self, which=KNIFE):
        self.weapon = which if isinstance(which, Melee) else weapon(_id_of(which))
        self.loaded = None
        self.reserve = None
        self.locked_for = 0.0

    @property
    def damage(self):
        return self.weapon.damage

    @property
    def status(self):
        """Never anything but usable."""
        return None

    @property
    def ready(self):
        return True

    def attack(self, muzzle, aim, damage):
        return Swing(
            *muzzle, *aim, damage=damage, reach=self.weapon.reach, arc=self.weapon.arc
        )

    def fire(self):
        return None

    def manual_reload(self):
        return None

    def refill(self):
        """Nothing to refill. A knife is never out."""

    def tick(self, dt=config.SIM_DT):
        return None


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
        self.locked_for = 0.0

    @property
    def damage(self):
        return self.weapon.damage

    @property
    def status(self):
        """Why this gun cannot be fired, or `None` if it can.

        The session used to hold this as one value for whichever weapon was in
        hand, which meant changing weapon cleared it: a gun put away mid-reload
        came back loaded and unlocked, and an empty one fired a free round on
        every swap. It belongs to the gun.
        """
        if self.locked_for > 0:
            return RELOAD
        if self.loaded <= 0:
            return NO_AMMO
        return None

    @property
    def ready(self):
        return self.status is None

    def attack(self, muzzle, aim, damage):
        return Shot(*muzzle, *aim, damage=damage)

    def fire(self):
        """Spend a round. Emptying the clip starts a reload if there is one.

        Only ever called on a gun that is `ready`, so there is no empty case to
        answer here -- `status` refuses the shot before it is taken rather than
        after the bullet has already been spawned.
        """
        self.loaded -= 1
        if self.loaded <= 0 and self.reserve > 0:
            self.reload()
        return self.status

    def reload(self):
        """Move as much of the reserve into the clip as will go, and lock the
        gun for as long as that takes.

        Four branches asking whether the clip was empty and whether the reserve
        could fill it, each with `60` written into it, say exactly this. Nothing
        loads a clip past its size, so there is no negative case to guard.
        """
        taken = min(self.weapon.clip - self.loaded, self.reserve)
        self.loaded += taken
        self.reserve -= taken
        self.locked_for = self.weapon.reload_seconds
        return RELOAD

    def manual_reload(self):
        if self.reserve > 0:
            return self.reload()
        return self.status

    def refill(self):
        self.reserve = self.weapon.reserve

    def tick(self, dt=config.SIM_DT):
        """Work off the reload, in hand or not.

        A gun stowed mid-reload goes on reloading. Pausing it would make the
        lockout escapable by tapping two number keys, and the lockout is the
        entire cost of reloading.
        """
        self.locked_for = max(0.0, self.locked_for - dt)
        return self.status


def _id_of(which):
    return which.id if isinstance(which, items.Item) else which
