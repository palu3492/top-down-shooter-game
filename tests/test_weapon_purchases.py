"""Neutral weapon purchases mutate wallet and loadout transactionally."""

import ast
from pathlib import Path

from shooter.loadout import Loadout
from shooter.modes.zombie_survival.state import SurvivalWallet
from shooter.weapon_purchases import (
    FULL_RESERVE,
    INSUFFICIENT_CASH,
    INVALID_OFFER,
    REFILLED,
    REPLACED,
    UNKNOWN_WEAPON,
    WeaponCatalog,
    WeaponPurchaseService,
)
from shooter.weapon_state import EquippedWeapon, WeaponDefinition


RIFLE = WeaponDefinition("rifle", "ballistic", 20, 6, 30, 90, 1, "556")
SMG = WeaponDefinition("smg", "ballistic", 12, 12, 40, 200, 1, "9mm")


def test_purchase_replaces_selected_weapon_only_after_affordability_validation():
    service = WeaponPurchaseService()
    catalog = WeaponCatalog((RIFLE, SMG))
    loadout = Loadout((EquippedWeapon(RIFLE),), capacity=1)
    wallet = SurvivalWallet(99)

    refused = service.purchase(
        (("weapon_id", "smg"), ("price", "100")), catalog, loadout, wallet
    )
    assert refused.reason == INSUFFICIENT_CASH
    assert loadout.selected.definition.definition_id == "rifle"
    assert wallet.balance == 99

    wallet.increase_cash(1)
    bought = service.purchase(
        (("weapon_id", "smg"), ("price", "100")), catalog, loadout, wallet
    )
    assert (bought.success, bought.action) == (True, REPLACED)
    assert loadout.selected.definition.definition_id == "smg"
    assert wallet.balance == 0


def test_owned_weapon_refills_or_rejects_full_reserve_without_charging():
    service = WeaponPurchaseService()
    held = EquippedWeapon(SMG)
    loadout = Loadout((held,), capacity=1)
    wallet = SurvivalWallet(100)
    offer = (("weapon_id", "smg"), ("price", "25"))

    full = service.purchase(offer, WeaponCatalog((SMG,)), loadout, wallet)
    assert full.reason == FULL_RESERVE
    assert wallet.balance == 100

    held.runtime.reserve = 20
    refilled = service.purchase(offer, WeaponCatalog((SMG,)), loadout, wallet)
    assert (refilled.success, refilled.action) == (True, REFILLED)
    assert held.runtime.reserve == 200
    assert wallet.balance == 75


def test_invalid_and_unknown_authored_offers_do_not_mutate_state():
    service = WeaponPurchaseService()
    loadout = Loadout((EquippedWeapon(RIFLE),), capacity=1)
    wallet = SurvivalWallet(500)

    invalid = service.purchase(
        (("weapon_id", "smg"), ("price", "nope")),
        WeaponCatalog((RIFLE,)),
        loadout,
        wallet,
    )
    unknown = service.purchase(
        (("weapon_id", "missing"), ("price", "10")),
        WeaponCatalog((RIFLE,)),
        loadout,
        wallet,
    )

    assert (invalid.reason, unknown.reason) == (INVALID_OFFER, UNKNOWN_WEAPON)
    assert wallet.balance == 500
    assert loadout.selected.definition.definition_id == "rifle"


def test_purchase_service_has_no_pygame_or_mode_dependency():
    imports = set()
    source = Path("shooter/weapon_purchases.py").read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any(
        name == "pygame" or name.startswith("shooter.modes") for name in imports
    )
