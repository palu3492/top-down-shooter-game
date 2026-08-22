"""Immutable presentation-only facts not yet owned by neutral Match state."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShopOfferStatus:
    slot: int
    weapon_id: str
    name: str
    price: int
    affordable: bool
    owned: bool


@dataclass(frozen=True, slots=True)
class SessionPresentationStatus:
    grenades: int
    stun_grenades: int
    instakill_remaining: float
    cargo: tuple[tuple[str, int], ...]
    notice: str | None = None
    interaction: str | None = None
    shopping: bool = False
    shop_feedback: str | None = None
    shop_offers: tuple[ShopOfferStatus, ...] = ()
