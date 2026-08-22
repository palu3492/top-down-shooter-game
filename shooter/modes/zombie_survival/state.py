"""Mutable state owned by one Zombie Survival match."""

from dataclasses import dataclass, field

LOST = "LOST"


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


@dataclass
class SurvivalState:
    cash: SurvivalWallet = field(default_factory=SurvivalWallet)

    @staticmethod
    def outcome(player_alive, rules_outcome=None):
        return rules_outcome if player_alive else LOST

