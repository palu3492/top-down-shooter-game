"""Transactional weapon purchases over neutral wallets and loadouts."""

from dataclasses import dataclass

from shooter.weapon_state import EquippedWeapon

PURCHASED = "purchased"
REPLACED = "replaced"
REFILLED = "refilled"
INVALID_OFFER = "invalid_offer"
UNKNOWN_WEAPON = "unknown_weapon"
INSUFFICIENT_CASH = "insufficient_cash"
FULL_RESERVE = "full_reserve"


class WeaponCatalog:
    def __init__(self, definitions=()):
        self._definitions = {}
        for definition in definitions:
            if definition.definition_id in self._definitions:
                raise ValueError(f"duplicate weapon: {definition.definition_id}")
            self._definitions[definition.definition_id] = definition

    def get(self, weapon_id):
        return self._definitions.get(weapon_id)


@dataclass(frozen=True, slots=True)
class WeaponPurchaseResult:
    success: bool
    reason: str
    weapon_id: str | None
    price: int | None
    balance: int
    action: str | None = None


class WeaponPurchaseService:
    def purchase(self, properties, catalog, loadout, wallet):
        values = dict(properties)
        weapon_id = values.get("weapon_id")
        try:
            price = int(values["price"])
        except (KeyError, TypeError, ValueError):
            return self._result(False, INVALID_OFFER, weapon_id, None, wallet)
        if not weapon_id or price < 0:
            return self._result(False, INVALID_OFFER, weapon_id, price, wallet)
        definition = catalog.get(weapon_id)
        if definition is None:
            return self._result(False, UNKNOWN_WEAPON, weapon_id, price, wallet)
        if wallet.balance < price:
            return self._result(False, INSUFFICIENT_CASH, weapon_id, price, wallet)

        existing = loadout.find(
            lambda held: held.definition.definition_id == weapon_id
        )
        if existing is not None:
            if (
                definition.reserve_capacity is None
                or existing.runtime.reserve >= definition.reserve_capacity
            ):
                return self._result(False, FULL_RESERVE, weapon_id, price, wallet)
            existing.runtime.reserve = definition.reserve_capacity
            wallet.cash_add_remove(-price)
            return self._result(True, REFILLED, weapon_id, price, wallet, REFILLED)

        equipped = EquippedWeapon(definition)
        if loadout.full:
            entries = list(loadout)
            entries[loadout.selected_index] = equipped
            loadout.replace(entries, selected=loadout.selected_index)
            action = REPLACED
        else:
            loadout.add(equipped, select=True)
            action = PURCHASED
        wallet.cash_add_remove(-price)
        return self._result(True, action, weapon_id, price, wallet, action)

    @staticmethod
    def _result(success, reason, weapon_id, price, wallet, action=None):
        return WeaponPurchaseResult(
            success, reason, weapon_id, price, wallet.balance, action
        )
