"""Attributed, relationship-aware damage independent of actor classes."""

from dataclasses import dataclass

from shooter.combat_state import CombatStateStore
from shooter.domain_events import DamageApplied, EntityKilled
from shooter.world_registry import EntityId

APPLIED = "applied"
FRIENDLY = "friendly"
NEUTRAL = "neutral"
SELF = "self"
MISSING_TARGET = "missing_target"
ALREADY_DEPLETED = "already_depleted"
INVALID_AMOUNT = "invalid_amount"


@dataclass(frozen=True, slots=True)
class DamageRequest:
    instigator_id: EntityId | None
    source_id: EntityId | None
    target_id: EntityId
    amount: float
    damage_type: str
    tick: int
    weapon_id: str | None = None


@dataclass(frozen=True, slots=True)
class DamageResult:
    request: DamageRequest
    applied: bool
    reason: str
    absorbed: float = 0.0
    health_damage: float = 0.0
    lethal: bool = False


class FactionStore:
    def __init__(self):
        self._factions = {}

    def assign(self, entity_id: EntityId, faction: str):
        self._factions[entity_id] = faction

    def faction_of(self, entity_id: EntityId | None):
        return None if entity_id is None else self._factions.get(entity_id)

    def remove(self, entity_id: EntityId):
        return self._factions.pop(entity_id, None)

    def __len__(self):
        return len(self._factions)

    def clear(self):
        self._factions.clear()


class RelationshipPolicy:
    def __init__(
        self,
        hostile_pairs=(),
        *,
        friendly_fire=False,
        self_damage=False,
        neutral_damage=False,
    ):
        self.hostile_pairs = frozenset(
            frozenset((left, right)) for left, right in hostile_pairs
        )
        self.friendly_fire = friendly_fire
        self.self_damage = self_damage
        self.neutral_damage = neutral_damage

    def decision(self, instigator_id, target_id, factions):
        if instigator_id is None:
            return True, APPLIED
        if instigator_id == target_id:
            return self.self_damage, APPLIED if self.self_damage else SELF

        source_faction = factions.faction_of(instigator_id)
        target_faction = factions.faction_of(target_id)
        if source_faction is None or target_faction is None:
            return self.neutral_damage, APPLIED if self.neutral_damage else NEUTRAL
        if source_faction == target_faction:
            return self.friendly_fire, APPLIED if self.friendly_fire else FRIENDLY
        if frozenset((source_faction, target_faction)) in self.hostile_pairs:
            return True, APPLIED
        return self.neutral_damage, APPLIED if self.neutral_damage else NEUTRAL


class DamageService:
    def __init__(self, combat, factions, relationships, events=None):
        self.combat: CombatStateStore = combat
        self.factions: FactionStore = factions
        self.relationships: RelationshipPolicy = relationships
        self.events = events

    def apply(self, request):
        if request.amount < 0:
            return DamageResult(request, False, INVALID_AMOUNT)
        if request.target_id not in self.combat:
            return DamageResult(request, False, MISSING_TARGET)

        before = self.combat.get(request.target_id)
        if before.depleted:
            return DamageResult(request, False, ALREADY_DEPLETED)

        allowed, reason = self.relationships.decision(
            request.instigator_id, request.target_id, self.factions
        )
        if not allowed:
            return DamageResult(request, False, reason)

        depletion = self.combat.deplete(request.target_id, request.amount)
        result = DamageResult(
            request=request,
            applied=True,
            reason=APPLIED,
            absorbed=depletion.absorbed,
            health_damage=depletion.health_lost,
            lethal=depletion.before.alive and depletion.after.depleted,
        )
        if self.events is not None:
            self.events.publish(
                DamageApplied(
                    source_id=request.source_id,
                    target_id=request.target_id,
                    amount=request.amount,
                    instigator_id=request.instigator_id,
                    weapon_id=request.weapon_id,
                    damage_type=request.damage_type,
                    tick=request.tick,
                    absorbed=result.absorbed,
                    health_damage=result.health_damage,
                )
            )
            if result.lethal:
                self.events.publish(
                    EntityKilled(
                        entity_id=request.target_id,
                        killer_id=request.instigator_id,
                        source_id=request.source_id,
                        weapon_id=request.weapon_id,
                        damage_type=request.damage_type,
                        tick=request.tick,
                    )
                )
        return result
