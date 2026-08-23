"""Neutral durability and tool-capability rules for map-authored harvestables."""

from dataclasses import dataclass

from shooter.interaction_query import interaction_distance

HARVESTED = "harvested"
DEPLETED = "depleted"
OUT_OF_RANGE = "out_of_range"
INCOMPATIBLE_TOOL = "incompatible_tool"
INVALID_HARVESTABLE = "invalid_harvestable"


@dataclass(slots=True)
class HarvestableState:
    definition: object
    durability: float
    initial_durability: float
    resource_id: str | None = None
    resource_total: int = 0
    awarded: int = 0

    @property
    def depleted(self):
        return self.durability <= 0


@dataclass(frozen=True, slots=True)
class HarvestResult:
    success: bool
    reason: str
    harvestable_id: str | None
    remaining_durability: float | None
    resource_id: str | None = None
    resource_amount: int = 0


@dataclass(frozen=True, slots=True)
class HarvestContext:
    harvestable_id: str
    kind: str
    prompt: str


class HarvestingService:
    def create_states(self, definitions):
        states = {}
        for definition in definitions:
            values = dict(definition.properties)
            try:
                durability = float(values["durability"])
            except (KeyError, TypeError, ValueError):
                continue
            if durability <= 0 or definition.harvestable_id in states:
                continue
            resource_id = values.get("resource_id") or None
            try:
                resource_total = int(values.get("resource_yield", 0))
            except (TypeError, ValueError):
                resource_total = 0
            states[definition.harvestable_id] = HarvestableState(
                definition,
                durability,
                durability,
                resource_id,
                max(0, resource_total),
            )
        return states

    def nearest(self, states, position, reach):
        candidates = (
            (interaction_distance(state.definition, position), harvestable_id, state)
            for harvestable_id, state in states.items()
            if not state.depleted
        )
        eligible = [candidate for candidate in candidates if candidate[0] <= reach]
        return None if not eligible else min(eligible)[2]

    def discover(self, states, position, reach, tool):
        if tool is None:
            return None
        state = self.nearest(states, position, reach)
        if state is None:
            return None
        values = dict(state.definition.properties)
        resource = values.get("resource_id")
        resource_text = "" if not resource else f" FOR {resource.upper()}"
        return HarvestContext(
            state.definition.harvestable_id,
            state.definition.kind,
            f"PRESS Q: HARVEST {state.definition.kind.upper()}{resource_text}",
        )

    def harvest(self, tool, state):
        if state is None:
            return HarvestResult(False, OUT_OF_RANGE, None, None)
        if state.depleted:
            return HarvestResult(
                False, DEPLETED, state.definition.harvestable_id, state.durability
            )
        values = dict(state.definition.properties)
        required = values.get("required_tool_capability", "harvest")
        if required not in tool.definition.capabilities:
            return HarvestResult(
                False,
                INCOMPATIBLE_TOOL,
                state.definition.harvestable_id,
                state.durability,
            )
        state.durability = max(0.0, state.durability - tool.definition.damage)
        earned = int(
            state.resource_total * (state.initial_durability - state.durability)
            / state.initial_durability
        ) - state.awarded
        state.awarded += earned
        return HarvestResult(
            True,
            HARVESTED,
            state.definition.harvestable_id,
            state.durability,
            state.resource_id,
            earned,
        )
