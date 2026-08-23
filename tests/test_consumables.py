"""Carried consumable inventory and purchase policy."""

from shooter.combat_state import CombatStateStore
from shooter.consumables import ConsumableInventory, ConsumablePurchaseService
from shooter.modes.zombie_survival.state import SurvivalWallet


def test_health_pack_usage_restores_health_without_consuming_at_full_health():
    inventory = ConsumableInventory((("health_pack", 1),))
    combat = CombatStateStore()
    combat.attach(1, 100)

    full = inventory.use_health_pack("health_pack", 50, combat, 1)
    combat.deplete(1, 60)
    used = inventory.use_health_pack("health_pack", 50, combat, 1)

    assert (full.success, full.reason, full.remaining) == (False, "full_health", 1)
    assert (used.success, used.restored, used.remaining) == (True, 50, 0)
    assert combat.get(1).health == 90


def test_consumable_purchase_validates_authored_values_before_charging():
    inventory = ConsumableInventory()
    wallet = SurvivalWallet(100)
    service = ConsumablePurchaseService()

    invalid = service.purchase((("price", "x"),), inventory, wallet)
    poor = service.purchase(
        (("price", "150"), ("item_id", "health_pack")), inventory, wallet
    )
    bought = service.purchase(
        (("price", "50"), ("item_id", "health_pack"), ("amount", "2")),
        inventory,
        wallet,
    )

    assert (invalid.success, invalid.reason, invalid.balance) == (
        False,
        "invalid_station",
        100,
    )
    assert (poor.success, poor.reason, poor.balance) == (
        False,
        "insufficient_cash",
        100,
    )
    assert (bought.success, bought.amount, bought.balance) == (True, 2, 50)
    assert inventory.snapshot() == (("health_pack", 2),)
