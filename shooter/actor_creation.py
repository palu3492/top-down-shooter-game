"""Renderer-independent actor definitions and explicit creation requests."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActorDefinition:
    definition_id: str
    actor_kind: str
    faction: str
    max_health: float
    collision_size: tuple[float, float]
    movement_speed: float


@dataclass(frozen=True, slots=True)
class ActorCreationRequest:
    definition_id: str
    position: tuple[float, float]


@dataclass(frozen=True, slots=True)
class ActorCreationResult:
    definition_id: str
    actor_kind: str
    faction: str
    position: tuple[float, float]
    max_health: float
    collision_size: tuple[float, float]
    movement_speed: float


class ActorCreationService:
    def create(self, definition, request):
        if request.definition_id != definition.definition_id:
            raise ValueError(
                f"request {request.definition_id!r} does not match "
                f"definition {definition.definition_id!r}"
            )
        return ActorCreationResult(
            definition_id=definition.definition_id,
            actor_kind=definition.actor_kind,
            faction=definition.faction,
            position=tuple(request.position),
            max_health=definition.max_health,
            collision_size=definition.collision_size,
            movement_speed=definition.movement_speed,
        )


class NeutralActorFactory:
    """Adapt the shared spawn-service factory shape without creating a renderer."""

    def __init__(self, creation=None):
        self.creation = creation or ActorCreationService()

    def create(self, window, definition, request):
        return self.creation.create(definition, request)
