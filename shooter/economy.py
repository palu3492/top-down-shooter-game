"""Reusable purchase mechanics; modes decide which offers exist and their prices."""

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
    weapon: str
    price: int
    ammo: int

    @property
    def name(self):
        return weapons.weapon(self.weapon).name


def carrying(carried, offer):
    return next((held for held in carried if held.weapon.id == offer.weapon), None)


def _entries(carried):
    return carried if not isinstance(carried, Loadout) else tuple(carried)


def price_of(offer, carried):
    return offer.ammo if carrying(_entries(carried), offer) else offer.price


def buy(offer, cash, carried):
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

