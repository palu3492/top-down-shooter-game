"""Neutral resource recipes and authored-anchor barricade transactions."""

from dataclasses import dataclass

BUILT = "built"
REPAIRED = "repaired"
INSUFFICIENT_RESOURCES = "insufficient_resources"
INVALID_RECIPE = "invalid_recipe"
FULL_HEALTH = "full_health"


@dataclass(slots=True)
class BarricadeState:
    anchor: object
    health: int = 0
    max_health: int = 0

    @property
    def built(self):
        return self.max_health > 0

    @property
    def destroyed(self):
        return not self.built and self.health <= 0


@dataclass(frozen=True, slots=True)
class ConstructionResult:
    success: bool
    reason: str
    anchor_id: str
    health: int
    max_health: int


class ConstructionService:
    def create_states(self, anchors):
        return {anchor.anchor_id: BarricadeState(anchor) for anchor in anchors}

    def build_or_repair(self, state, resources):
        values = dict(state.anchor.properties)
        if not state.built:
            try:
                max_health = int(values["max_health"])
            except (KeyError, TypeError, ValueError):
                return self._result(False, INVALID_RECIPE, state)
            recipe = self._recipe(values.get("build_cost", ""))
            if max_health <= 0 or recipe is None:
                return self._result(False, INVALID_RECIPE, state)
            if not self._spend(recipe, resources):
                return self._result(False, INSUFFICIENT_RESOURCES, state)
            state.max_health = max_health
            state.health = max_health
            return self._result(True, BUILT, state)
        if state.health >= state.max_health:
            return self._result(False, FULL_HEALTH, state)
        recipe = self._recipe(values.get("repair_cost", values.get("build_cost", "")))
        if recipe is None:
            return self._result(False, INVALID_RECIPE, state)
        if not self._spend(recipe, resources):
            return self._result(False, INSUFFICIENT_RESOURCES, state)
        state.health = state.max_health
        return self._result(True, REPAIRED, state)

    def collision_obstacles(self, states):
        return tuple(
            state.anchor.area
            for state in states.values()
            if state.built and state.anchor.area is not None
        )

    def damage(self, state, amount):
        if amount < 0:
            raise ValueError("damage cannot be negative")
        if not state.built:
            return False
        state.health = max(0, state.health - amount)
        if state.health == 0:
            state.max_health = 0
            return True
        return False

    @staticmethod
    def _recipe(value):
        recipe = []
        for part in value.split(","):
            if not part:
                continue
            try:
                resource_id, amount = part.split(":", 1)
                amount = int(amount)
            except (ValueError, TypeError):
                return None
            if not resource_id or amount <= 0:
                return None
            recipe.append((resource_id, amount))
        return tuple(recipe) or None

    @staticmethod
    def _spend(recipe, resources):
        if any(resources.count(resource_id) < amount for resource_id, amount in recipe):
            return False
        for resource_id, amount in recipe:
            resources.spend(resource_id, amount)
        return True

    @staticmethod
    def _result(success, reason, state):
        return ConstructionResult(
            success, reason, state.anchor.anchor_id, state.health, state.max_health
        )
