"""Zombie Survival weapon-station stock and pricing policy."""

from shooter import weapons
from shooter.economy import (
    BOUGHT,
    NO_ROOM,
    REFILLED,
    STOCKED,
    TOO_POOR,
    Offer,
    buy,
    carrying,
    price_of,
)

STOCK = (
    Offer(weapons.M16.id, 500, 100),
    Offer(weapons.SHOTGUN.id, 750, 150),
    Offer(weapons.SMG.id, 900, 200),
    Offer(weapons.SNIPER.id, 1400, 300),
)

__all__ = (
    "BOUGHT",
    "NO_ROOM",
    "REFILLED",
    "STOCK",
    "STOCKED",
    "TOO_POOR",
    "Offer",
    "buy",
    "carrying",
    "price_of",
)

