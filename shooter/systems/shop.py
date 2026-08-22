"""What the gun stand sells, and what a purchase does.

No drawing here. The panel is `ui/shopfront.py`, because a shop that owns its
own rendering is `GunData` again -- and what a purchase costs is worth reading
without a `Surface` in the way.

`Cash.cash_add_remove` has returned whether a purchase can be afforded since
2019, with a comment saying so, and nothing had ever called it. This is what it
was for.
"""

from dataclasses import dataclass

from shooter import weapons
from shooter.loadout import Loadout

BOUGHT = "bought"
REFILLED = "refilled"
TOO_POOR = "too poor"
NO_ROOM = "no room"
STOCKED = "stocked"


@dataclass(frozen=True)
class Offer:
    """A weapon on the wall, and the two prices it has.

    Buying one you already carry is buying its ammunition, which is the cheaper
    number -- otherwise running dry would mean paying for the gun again.
    """

    weapon: str
    price: int
    ammo: int

    @property
    def name(self):
        return weapons.weapon(self.weapon).name


# The M16 is the stand's entry-level firearm.
STOCK = (
    Offer(weapons.M16.id, 500, 100),
    Offer(weapons.SHOTGUN.id, 750, 150),
    Offer(weapons.SMG.id, 900, 200),
    Offer(weapons.SNIPER.id, 1400, 300),
)


def carrying(carried, offer):
    """The one in hand-or-holster matching this offer, if there is one."""
    return next(
        (held for held in carried if held.weapon.id == offer.weapon),
        None,
    )


def _entries(carried):
    return carried if not isinstance(carried, Loadout) else tuple(carried)


def price_of(offer, carried):
    return offer.ammo if carrying(_entries(carried), offer) else offer.price


def buy(offer, cash, carried):
    """Take the money and hand over the goods; say what happened either way.

    Everything that could refuse the sale is checked before the coins move, so
    a refusal never costs the player anything.
    """
    entries = _entries(carried)
    held = carrying(entries, offer)

    if held is None and len(entries) >= weapons.MAX_SLOTS:
        return NO_ROOM
    if held is not None and held.reserve >= held.weapon.reserve:
        return STOCKED
    if not cash.cash_add_remove(-price_of(offer, entries)):
        return TOO_POOR

    if held is None:
        made = weapons.equip(offer.weapon)
        if isinstance(carried, Loadout):
            carried.add(made)
        else:
            carried.append(made)
        return BOUGHT
    held.refill()
    return REFILLED
