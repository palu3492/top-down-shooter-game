"""Headless attributed damage and relationship policy."""

from dataclasses import asdict
import json

from shooter.combat_state import CombatStateStore
from shooter.damage import (
    ALREADY_DEPLETED,
    FRIENDLY,
    NEUTRAL,
    SELF,
    DamageRequest,
    DamageService,
    FactionStore,
    RelationshipPolicy,
)
from shooter.domain_events import DamageApplied, EntityKilled, EventQueue
from shooter.world_registry import EntityId


def setup_service(**policy_options):
    combat = CombatStateStore()
    factions = FactionStore()
    policy = RelationshipPolicy(
        (("survivors", "horde"),),
        **policy_options,
    )
    return combat, factions, DamageService(combat, factions, policy)


def request(source, target, amount=25):
    return DamageRequest(
        instigator_id=source,
        source_id=EntityId(99),
        target_id=target,
        amount=amount,
        damage_type="ballistic",
        tick=42,
        weapon_id="rifle",
    )


def test_damage_attribution_contains_only_ids_and_primitive_metadata():
    made = request(EntityId(1), EntityId(2))

    assert json.loads(json.dumps(asdict(made))) == {
        "instigator_id": 1,
        "source_id": 99,
        "target_id": 2,
        "amount": 25,
        "damage_type": "ballistic",
        "tick": 42,
        "weapon_id": "rifle",
    }


def test_hostile_damage_reports_armor_health_and_first_lethal_transition():
    combat, factions, damage = setup_service()
    survivor = EntityId(1)
    enemy = EntityId(2)
    combat.attach(enemy, 20, armor=5, max_armor=5)
    factions.assign(survivor, "survivors")
    factions.assign(enemy, "horde")

    result = damage.apply(request(survivor, enemy, amount=25))
    repeated = damage.apply(request(survivor, enemy, amount=1))

    assert result.applied is True
    assert result.absorbed == 5
    assert result.health_damage == 20
    assert result.lethal is True
    assert repeated.applied is False
    assert repeated.reason == ALREADY_DEPLETED
    assert repeated.lethal is False


def test_friendly_neutral_and_self_damage_are_rejected_without_mutation():
    combat, factions, damage = setup_service()
    attacker = EntityId(1)
    friend = EntityId(2)
    neutral = EntityId(3)
    for entity_id in (attacker, friend, neutral):
        combat.attach(entity_id, 100)
    factions.assign(attacker, "survivors")
    factions.assign(friend, "survivors")

    friendly = damage.apply(request(attacker, friend))
    unrelated = damage.apply(request(attacker, neutral))
    self_hit = damage.apply(request(attacker, attacker))

    assert (friendly.reason, unrelated.reason, self_hit.reason) == (
        FRIENDLY,
        NEUTRAL,
        SELF,
    )
    unchanged = (attacker, friend, neutral)
    assert all(combat.get(entity_id).health == 100 for entity_id in unchanged)


def test_policy_can_enable_friendly_neutral_and_self_damage():
    combat, factions, damage = setup_service(
        friendly_fire=True,
        neutral_damage=True,
        self_damage=True,
    )
    attacker = EntityId(1)
    friend = EntityId(2)
    neutral = EntityId(3)
    for entity_id in (attacker, friend, neutral):
        combat.attach(entity_id, 100)
    factions.assign(attacker, "survivors")
    factions.assign(friend, "survivors")

    assert damage.apply(request(attacker, friend)).applied is True
    assert damage.apply(request(attacker, neutral)).applied is True
    assert damage.apply(request(attacker, attacker)).applied is True


def test_environmental_damage_does_not_need_faction_membership():
    combat, _, damage = setup_service()
    target = EntityId(4)
    combat.attach(target, 100)

    result = damage.apply(request(None, target, amount=10))

    assert result.applied is True
    assert combat.get(target).health == 90


def test_applied_damage_and_first_death_publish_once_with_attribution():
    combat = CombatStateStore()
    factions = FactionStore()
    events = EventQueue()
    attacker = EntityId(1)
    target = EntityId(2)
    combat.attach(target, 10)
    factions.assign(attacker, "survivors")
    factions.assign(target, "horde")
    damage = DamageService(
        combat,
        factions,
        RelationshipPolicy((("survivors", "horde"),)),
        events,
    )
    lethal = request(attacker, target, amount=10)

    damage.apply(lethal)
    damage.apply(lethal)

    assert events.drain() == (
        DamageApplied(
            source_id=EntityId(99),
            target_id=target,
            amount=10,
            instigator_id=attacker,
            weapon_id="rifle",
            damage_type="ballistic",
            tick=42,
            health_damage=10,
        ),
        EntityKilled(
            entity_id=target,
            killer_id=attacker,
            source_id=EntityId(99),
            weapon_id="rifle",
            damage_type="ballistic",
            tick=42,
        ),
    )
