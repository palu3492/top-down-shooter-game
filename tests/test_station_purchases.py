"""Reusable TMX-station purchase policies."""

from shooter.combat_state import CombatStateStore
from shooter.loadout import Loadout
from shooter.modes.zombie_survival.state import SurvivalWallet
from shooter.modes.zombie_survival.mode import RIFLE, SMG
from shooter.station_purchases import (
    FULL_AMMO,
    FULL_HEALTH,
    PURCHASED,
    StationPurchaseService,
)
from shooter.weapon_state import EquippedWeapon


def prepared():
    combat = CombatStateStore()
    combat.attach(1, 100)
    rifle = EquippedWeapon(RIFLE)
    smg = EquippedWeapon(SMG)
    return combat, Loadout((rifle, smg)), SurvivalWallet(1000)


def test_ammo_station_refills_every_eligible_firearm_transactionally():
    combat, loadout, wallet = prepared()
    loadout[0].runtime.reserve = 10
    loadout[1].runtime.reserve = 20

    result = StationPurchaseService().purchase(
        "ammo_station", (("price", "200"),), loadout, combat, 1, wallet
    )

    assert (result.success, result.reason, result.amount, result.balance) == (
        True,
        PURCHASED,
        RIFLE.reserve_capacity - 10 + SMG.reserve_capacity - 20,
        800,
    )
    assert [weapon.runtime.reserve for weapon in loadout] == [
        RIFLE.reserve_capacity,
        SMG.reserve_capacity,
    ]
    assert (
        StationPurchaseService().purchase(
            "ammo_station", (("price", "200"),), loadout, combat, 1, wallet
        ).reason
        == FULL_AMMO
    )


def test_health_and_armor_stations_restore_with_authored_limits():
    combat, loadout, wallet = prepared()
    combat.deplete(1, 45)

    health = StationPurchaseService().purchase(
        "health_station",
        (("price", "150"), ("health_amount", "30")),
        loadout,
        combat,
        1,
        wallet,
    )
    armor = StationPurchaseService().purchase(
        "armor_station",
        (("price", "250"), ("armor_amount", "80"), ("armor_capacity", "100")),
        loadout,
        combat,
        1,
        wallet,
    )

    assert (health.success, health.amount, health.balance) == (True, 30, 850)
    assert (armor.success, armor.amount, armor.balance) == (True, 80, 600)
    assert combat.get(1).health == 85
    assert (combat.get(1).armor, combat.get(1).max_armor) == (80, 100)
    assert (
        StationPurchaseService().purchase(
            "health_station",
            (("price", "150"), ("health_amount", "30")),
            loadout,
            combat,
            1,
            wallet,
        ).reason
        != FULL_HEALTH
    )
