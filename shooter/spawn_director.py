"""Reusable deterministic pacing for budgeted actor spawning."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpawnDirectorPolicy:
    burst_size: int = 2
    interval_seconds: float = 1.0
    activation_delay_seconds: float = 0.0

    def __post_init__(self):
        if self.burst_size < 1:
            raise ValueError("burst_size must be at least one")
        if self.interval_seconds < 0:
            raise ValueError("interval_seconds cannot be negative")
        if self.activation_delay_seconds < 0:
            raise ValueError("activation_delay_seconds cannot be negative")


@dataclass(frozen=True, slots=True)
class SpawnBudget:
    definition: object
    count: int

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("spawn count cannot be negative")


@dataclass(frozen=True, slots=True)
class SpawnRelease:
    definition: object
    count: int
    sequence: int
    activation_delay_seconds: float


class SpawnDirector:
    """Turn ordered actor budgets into frame-rate-independent paced releases.

    The director owns only scheduling. A mode supplies definitions and turns each
    release into a normal shared spawn request with its own placement policy.
    """

    def __init__(self, policy=None):
        self.policy = SpawnDirectorPolicy() if policy is None else policy
        self._pending = []
        self._cooldown = 0.0
        self._sequence = 0

    @property
    def pending(self):
        return tuple((budget.definition, budget.count) for budget in self._pending)

    @property
    def remaining(self):
        return sum(budget.count for budget in self._pending)

    @property
    def active(self):
        return bool(self._pending)

    def queue(self, budgets):
        if self._pending:
            raise RuntimeError("cannot replace an active spawn budget")
        self._pending = [budget for budget in budgets if budget.count]
        self._cooldown = 0.0
        self._sequence = 0

    def clear(self):
        self._pending.clear()
        self._cooldown = 0.0

    def advance(self, dt):
        if dt < 0:
            raise ValueError("dt cannot be negative")
        if not self._pending:
            return ()
        self._cooldown -= dt
        releases = []
        while self._pending and self._cooldown <= 0:
            budget = self._pending[0]
            count = min(self.policy.burst_size, budget.count)
            releases.append(
                SpawnRelease(
                    budget.definition,
                    count,
                    self._sequence,
                    self.policy.activation_delay_seconds,
                )
            )
            self._sequence += 1
            remaining = budget.count - count
            if remaining:
                self._pending[0] = SpawnBudget(budget.definition, remaining)
            else:
                self._pending.pop(0)
            if self.policy.interval_seconds == 0:
                continue
            self._cooldown += self.policy.interval_seconds
        return tuple(releases)
