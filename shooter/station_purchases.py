"""Reusable transactional policies for map-authored preparation stations."""

from dataclasses import dataclass

from shooter.weapon_state import REFILL, WeaponOperationRequest

INVALID_STATION = "invalid_station"
INSUFFICIENT_CASH = "insufficient_cash"
FULL_AMMO = "full_ammo"
FULL_HEALTH = "full_health"
FULL_ARMOR = "full_armor"
PURCHASED = "purchased"


@dataclass(frozen=True, slots=True)
class StationPurchaseResult:
    success: bool
    reason: str
    kind: str
    price: int | None
    balance: int
    amount: float = 0.0


class StationPurchaseService:
    """Apply an authored station's effect after validating its price and state."""

    def purchase(self, kind, properties, loadout, combat, actor_id, wallet):
        values = dict(properties)
        try:
            price = int(values["price"])
        except (KeyError, TypeError, ValueError):
            return self._result(False, INVALID_STATION, kind, None, wallet)
        if price < 0:
            return self._result(False, INVALID_STATION, kind, price, wallet)
        if wallet.balance < price:
            return self._result(False, INSUFFICIENT_CASH, kind, price, wallet)
        if kind == "ammo_station":
            return self._refill_ammo(price, loadout, wallet)
        if kind == "health_station":
            return self._restore_health(price, values, combat, actor_id, wallet)
        if kind == "armor_station":
            return self._restore_armor(price, values, combat, actor_id, wallet)
        return self._result(False, INVALID_STATION, kind, price, wallet)

    def _refill_ammo(self, price, loadout, wallet):
        added = sum(
            held.operations.apply(
                held.definition, held.runtime, WeaponOperationRequest(REFILL)
            ).rounds_loaded
            for held in loadout
            if held.definition.reserve_capacity is not None
            and held.runtime.reserve < held.definition.reserve_capacity
        )
        if added == 0:
            return self._result(False, FULL_AMMO, "ammo_station", price, wallet)
        wallet.cash_add_remove(-price)
        return self._result(True, PURCHASED, "ammo_station", price, wallet, added)

    def _restore_health(self, price, values, combat, actor_id, wallet):
        amount = self._amount(values, "health_amount")
        if amount is None:
            return self._result(False, INVALID_STATION, "health_station", price, wallet)
        before = combat.get(actor_id)
        after = combat.restore(actor_id, health=amount)
        restored = after.health - before.health
        if restored == 0:
            return self._result(False, FULL_HEALTH, "health_station", price, wallet)
        wallet.cash_add_remove(-price)
        return self._result(True, PURCHASED, "health_station", price, wallet, restored)

    def _restore_armor(self, price, values, combat, actor_id, wallet):
        amount = self._amount(values, "armor_amount")
        capacity = self._amount(values, "armor_capacity")
        if amount is None or capacity is None:
            return self._result(False, INVALID_STATION, "armor_station", price, wallet)
        before = combat.get(actor_id)
        after = combat.grant_armor(actor_id, amount, capacity)
        restored = after.armor - before.armor
        if restored == 0:
            return self._result(False, FULL_ARMOR, "armor_station", price, wallet)
        wallet.cash_add_remove(-price)
        return self._result(True, PURCHASED, "armor_station", price, wallet, restored)

    @staticmethod
    def _amount(values, name):
        try:
            amount = float(values[name])
        except (KeyError, TypeError, ValueError):
            return None
        return amount if amount > 0 else None

    @staticmethod
    def _result(success, reason, kind, price, wallet, amount=0.0):
        return StationPurchaseResult(
            success, reason, kind, price, wallet.balance, amount
        )
