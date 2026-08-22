"""Ordered, match-scoped domain facts at the first extraction seam."""

from dataclasses import asdict
import json

from shooter.domain_events import (
    DamageApplied,
    EntityKilled,
    EntityRegistered,
    EntityRemoved,
    EventQueue,
)
from shooter.entities.zombie import Zombie
from shooter.session import Session
from shooter.viewport import Viewport
from shooter.world_registry import EntityId, WorldRegistry

WINDOW = (1080, 720)


def test_event_values_are_immutable_primitive_facts():
    damaged = DamageApplied(EntityId(1), EntityId(2), 12.5)
    killed = EntityKilled(EntityId(2), EntityId(1))

    assert json.loads(json.dumps(asdict(damaged))) == {
        "source_id": 1,
        "target_id": 2,
        "amount": 12.5,
        "instigator_id": None,
        "weapon_id": None,
        "damage_type": "",
        "tick": 0,
        "absorbed": 0.0,
        "health_damage": 0.0,
    }
    assert asdict(killed) == {
        "entity_id": 2,
        "killer_id": 1,
        "source_id": None,
        "weapon_id": None,
        "damage_type": "",
        "tick": 0,
    }


def test_queue_preserves_order_and_drains_each_fact_once():
    events = EventQueue()
    registered = EntityRegistered(EntityId(1), ("actor", "player"))
    removed = EntityRemoved(EntityId(1), "match_end")

    events.publish(registered)
    events.publish(removed)

    assert events.drain() == (registered, removed)
    assert events.drain() == ()


def test_queues_and_registries_are_match_scoped():
    first_events = EventQueue()
    second_events = EventQueue()
    first = WorldRegistry(first_events)
    second = WorldRegistry(second_events)

    first.register(object(), ("first",))

    assert len(first_events) == 1
    assert len(second_events) == 0
    assert len(first) == 1
    assert len(second) == 0


def test_session_bridge_emits_enemy_lifecycle_once(display, cash):
    session = Session(Viewport(WINDOW))
    opening = session.events.drain()
    enemy = Zombie(WINDOW, cash)

    session.zombies.add(enemy)
    session._sync_enemy_registry()
    enemy_id = session.entities.id_for(enemy)
    registered = session.events.drain()
    session._sync_enemy_registry()

    assert opening == (EntityRegistered(session.player_id, ("actor", "player")),)
    assert registered == (EntityRegistered(enemy_id, ("actor", "enemy")),)
    assert session.events.drain() == ()

    enemy.kill()
    session._sync_enemy_registry()

    assert session.events.drain() == (
        EntityRemoved(enemy_id, "despawned"),
    )
