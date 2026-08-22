"""Mutable state owned by one Zombie Survival match."""

from dataclasses import dataclass, field

LOST = "LOST"


@dataclass(frozen=True, slots=True)
class SurvivalStatus:
    phase: str
    wave: int
    preparation_remaining: float
    cash: int
    enemies_remaining: int
    outcome: str | None = None
    wave_target: int | None = None
    title: str = "Zombie Survival"


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
