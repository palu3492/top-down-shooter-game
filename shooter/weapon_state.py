"""Renderer-independent weapon definitions and per-instance operation state."""

from dataclasses import dataclass

NO_AMMO = "no ammo"
RELOAD = "reload"

BEGIN_ATTACK = "begin_attack"
FIRE = "fire"
MANUAL_RELOAD = "manual_reload"
REFILL = "refill"
ADVANCE = "advance"


@dataclass(frozen=True, slots=True)
class WeaponDefinition:
    """Immutable configuration shared by every instance of a weapon kind."""

    definition_id: str
    attack_kind: str
    damage: float
    rate: float
    magazine_capacity: int | None = None
    reserve_capacity: int | None = None
    reload_seconds: float = 0.0
    ammo_id: str | None = None
    pellets: int = 1
    spread: float = 0.0
    automatic: bool = False
    max_range: float | None = None
    effective_range: float | None = None
    minimum_damage_fraction: float = 1.0
    reach: float | None = None
    arc: float | None = None
    capabilities: frozenset[str] = frozenset()


@dataclass(slots=True)
class WeaponRuntime:
    """Mutable operation state owned by one equipped weapon instance."""

    definition_id: str
    loaded: int | None
    reserve: int | None
    cooldown_remaining: float = 0.0
    reload_remaining: float = 0.0

    @classmethod
    def fresh(cls, definition: WeaponDefinition):
        return cls(
            definition_id=definition.definition_id,
            loaded=definition.magazine_capacity,
            reserve=definition.reserve_capacity,
        )


@dataclass(frozen=True, slots=True)
class WeaponOperationRequest:
    action: str
    elapsed: float = 0.0


@dataclass(frozen=True, slots=True)
class WeaponOperationResult:
    accepted: bool
    status: str | None
    rounds_spent: int = 0
    rounds_loaded: int = 0


class WeaponOperationService:
    """Apply weapon rules without knowing who owns or presents the weapon."""

    def __init__(self, spent_epsilon=1e-9):
        self.spent_epsilon = spent_epsilon

    def status(self, definition, runtime):
        if runtime.reload_remaining > self.spent_epsilon:
            return RELOAD
        if definition.magazine_capacity is not None and runtime.loaded <= 0:
            return NO_AMMO
        return None

    def ready(self, definition, runtime):
        return (
            self.status(definition, runtime) is None
            and runtime.cooldown_remaining <= self.spent_epsilon
        )

    def apply(self, definition, runtime, request):
        if request.action == ADVANCE:
            runtime.cooldown_remaining = max(
                0.0, runtime.cooldown_remaining - request.elapsed
            )
            runtime.reload_remaining = max(
                0.0, runtime.reload_remaining - request.elapsed
            )
            return WeaponOperationResult(True, self.status(definition, runtime))

        if request.action == BEGIN_ATTACK:
            if not self.ready(definition, runtime):
                return WeaponOperationResult(False, self.status(definition, runtime))
            runtime.cooldown_remaining = 1 / definition.rate
            return WeaponOperationResult(True, self.status(definition, runtime))

        if request.action == FIRE:
            if definition.magazine_capacity is None:
                return WeaponOperationResult(True, None)
            if runtime.loaded <= 0:
                return WeaponOperationResult(False, self.status(definition, runtime))
            runtime.loaded -= 1
            if runtime.loaded <= 0 and runtime.reserve > 0:
                loaded = self._reload(definition, runtime)
                return WeaponOperationResult(True, RELOAD, 1, loaded)
            return WeaponOperationResult(
                True, self.status(definition, runtime), rounds_spent=1
            )

        if request.action == MANUAL_RELOAD:
            if definition.magazine_capacity is None or runtime.reserve <= 0:
                return WeaponOperationResult(False, self.status(definition, runtime))
            loaded = self._reload(definition, runtime)
            return WeaponOperationResult(True, RELOAD, rounds_loaded=loaded)

        if request.action == REFILL:
            if definition.reserve_capacity is None:
                return WeaponOperationResult(False, self.status(definition, runtime))
            added = definition.reserve_capacity - runtime.reserve
            runtime.reserve = definition.reserve_capacity
            return WeaponOperationResult(
                True, self.status(definition, runtime), rounds_loaded=added
            )

        raise ValueError(f"unknown weapon operation: {request.action}")

    @staticmethod
    def _reload(definition, runtime):
        taken = min(definition.magazine_capacity - runtime.loaded, runtime.reserve)
        runtime.loaded += taken
        runtime.reserve -= taken
        runtime.reload_remaining = definition.reload_seconds
        return taken


class EquippedWeapon:
    """One owner-independent weapon definition plus its mutable runtime."""

    def __init__(self, definition, runtime=None, operations=None):
        self.definition = definition
        self.runtime = runtime or WeaponRuntime.fresh(definition)
        self.operations = operations or WeaponOperationService()

    @property
    def ready(self):
        return self.operations.ready(self.definition, self.runtime)

    @property
    def status(self):
        return self.operations.status(self.definition, self.runtime)

    def advance(self, elapsed):
        return self.operations.apply(
            self.definition,
            self.runtime,
            WeaponOperationRequest(ADVANCE, elapsed),
        )

    def fire(self):
        begun = self.operations.apply(
            self.definition,
            self.runtime,
            WeaponOperationRequest(BEGIN_ATTACK),
        )
        if not begun.accepted:
            return begun
        return self.operations.apply(
            self.definition, self.runtime, WeaponOperationRequest(FIRE)
        )

    def reload(self):
        return self.operations.apply(
            self.definition,
            self.runtime,
            WeaponOperationRequest(MANUAL_RELOAD),
        )
