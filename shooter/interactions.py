"""Neutral interaction discovery and intent routing values."""

from dataclasses import dataclass

from shooter.interaction_query import nearest_interaction

AVAILABLE = "available"
OUT_OF_RANGE = "out_of_range"


@dataclass(frozen=True, slots=True)
class InteractionContext:
    actor_id: int
    interaction_id: str
    kind: str
    prompt: str
    properties: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class InteractionIntentResult:
    available: bool
    reason: str
    actor_id: int
    interaction_id: str | None = None
    kind: str | None = None


class InteractionService:
    def discover(self, actor_id, position, interactions, max_distance):
        interaction = nearest_interaction(
            interactions, position, max_distance
        )
        if interaction is None:
            return None
        properties = dict(interaction.properties)
        prompt = properties.get(
            "prompt", f"PRESS E: {interaction.kind.replace('_', ' ').upper()}"
        )
        return InteractionContext(
            int(actor_id),
            interaction.interaction_id,
            interaction.kind,
            prompt,
            interaction.properties,
        )

    def route_intent(self, actor_id, context):
        if context is None or context.actor_id != actor_id:
            return InteractionIntentResult(False, OUT_OF_RANGE, int(actor_id))
        return InteractionIntentResult(
            True,
            AVAILABLE,
            int(actor_id),
            context.interaction_id,
            context.kind,
        )
