"""Reusable stackable consumables owned by a match, not the UI."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConsumableUseResult:
    success: bool
    reason: str
    item_id: str
    remaining: int
    restored: float = 0.0


@dataclass(frozen=True, slots=True)
class ConsumablePurchaseResult:
    success: bool
    reason: str
    item_id: str | None
    amount: int
    price: int | None
    balance: int


class ConsumableInventory:
    def __init__(self, quantities=()):
        self._quantities = dict(quantities)

    def count(self, item_id):
        return self._quantities.get(item_id, 0)

    def add(self, item_id, amount=1):
        if not item_id or amount < 0:
            raise ValueError("consumable additions require an item and valid amount")
        self._quantities[item_id] = self.count(item_id) + int(amount)

    def use_health_pack(self, item_id, health_amount, combat, actor_id):
        if self.count(item_id) <= 0:
            return ConsumableUseResult(False, "none_owned", item_id, 0)
        before = combat.get(actor_id)
        after = combat.restore(actor_id, health=health_amount)
        restored = after.health - before.health
        if restored <= 0:
            return ConsumableUseResult(
                False, "full_health", item_id, self.count(item_id)
            )
        self._quantities[item_id] -= 1
        return ConsumableUseResult(True, "used", item_id, self.count(item_id), restored)

    def use_armor_plate(self, item_id, armor_amount, armor_capacity, combat, actor_id):
        if self.count(item_id) <= 0:
            return ConsumableUseResult(False, "none_owned", item_id, 0)
        before = combat.get(actor_id)
        after = combat.grant_armor(actor_id, armor_amount, armor_capacity)
        restored = after.armor - before.armor
        if restored <= 0:
            return ConsumableUseResult(False, "full_armor", item_id, self.count(item_id))
        self._quantities[item_id] -= 1
        return ConsumableUseResult(True, "used", item_id, self.count(item_id), restored)

    def snapshot(self):
        return tuple(sorted(self._quantities.items()))


class ConsumablePurchaseService:
    """Transactional purchase policy for map-authored carried consumables."""

    def purchase(self, properties, inventory, wallet):
        values = dict(properties)
        item_id = values.get("item_id")
        try:
            price = int(values["price"])
            amount = int(values.get("amount", 1))
        except (KeyError, TypeError, ValueError):
            return self._result(False, "invalid_station", None, 0, None, wallet)
        if not item_id or price < 0 or amount < 1:
            return self._result(
                False, "invalid_station", item_id, amount, price, wallet
            )
        if wallet.balance < price:
            return self._result(
                False, "insufficient_cash", item_id, amount, price, wallet
            )
        inventory.add(item_id, amount)
        wallet.cash_add_remove(-price)
        return self._result(True, "purchased", item_id, amount, price, wallet)

    @staticmethod
    def _result(success, reason, item_id, amount, price, wallet):
        return ConsumablePurchaseResult(
            success, reason, item_id, amount, price, wallet.balance
        )
