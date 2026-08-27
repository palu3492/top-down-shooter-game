"""Mutable state owned by one Zombie Survival match."""

from dataclasses import dataclass, field

from shooter.interactions import InteractionContext, InteractionIntentResult
from shooter.harvesting import HarvestContext, HarvestResult
from shooter.construction import ConstructionResult
from shooter.weapon_purchases import WeaponPurchaseResult
from shooter.station_purchases import StationPurchaseResult
from shooter.consumables import ConsumablePurchaseResult, ConsumableUseResult

LOST = "LOST"


@dataclass(frozen=True, slots=True)
class BallisticTrace:
    """A short-lived, snapshot-safe visual for a resolved firearm shot."""

    origin: tuple[float, float]
    direction: tuple[float, float]
    speed: float
    elapsed: float
    remaining: float


@dataclass(frozen=True, slots=True)
class SurvivalStatus:
    phase: str
    wave: int
    preparation_remaining: float
    cash: int
    enemies_remaining: int
    active_equipment: str | None = None
    consumables: tuple[tuple[str, int], ...] = ()
    pending_enemies: int = 0
    activating_enemies: int = 0
    outcome: str | None = None
    wave_target: int | None = None
    title: str = "Zombie Survival"
    enemy_composition: tuple[tuple[str, int], ...] = ()
    interaction_context: InteractionContext | None = None
    interaction_result: InteractionIntentResult | None = None
    purchase_result: WeaponPurchaseResult | None = None
    station_result: StationPurchaseResult | None = None
    consumable_purchase_result: ConsumablePurchaseResult | None = None
    health_pack_result: ConsumableUseResult | None = None
    harvest_result: HarvestResult | None = None
    harvest_context: HarvestContext | None = None
    resources: tuple[tuple[str, int], ...] = ()
    construction_result: ConstructionResult | None = None
    ballistic_traces: tuple[BallisticTrace, ...] = ()
    recovering_enemies: int = 0
    navigation_cell_size: int | None = None
    navigation_goal: tuple[int, int] | None = None
    navigation_reachable_cells: int = 0
    navigation_route_requests: int = 0
    navigation_route_cache_hits: int = 0
    stuck_enemy_ids: tuple[int, ...] = ()


class SurvivalWallet:
    def __init__(self, balance=0):
        self.balance = balance

    def increase_cash(self, amount):
        self.balance += amount

    def cash_add_remove(self, amount):
        if self.balance + amount < 0:
            return False
        self.balance += amount
        return True

    # Compatibility name for callers that predate the neutral wallet. It is a
    # view of the same value, not a second presentation-owned cash balance.
    @property
    def cash_amount(self):
        return self.balance

    @cash_amount.setter
    def cash_amount(self, value):
        self.balance = value


@dataclass
class SurvivalState:
    cash: SurvivalWallet = field(default_factory=SurvivalWallet)

    @staticmethod
    def outcome(player_alive, rules_outcome=None):
        return rules_outcome if player_alive else LOST
