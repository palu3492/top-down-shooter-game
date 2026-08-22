"""Reusable health and optional armor independent of actor implementations."""

import pytest

from shooter import config
from shooter.combat_state import CombatStateStore, VitalState
from shooter.entities.zombie import Zombie
from shooter.session import Session
from shooter.viewport import Viewport
from shooter.world_registry import EntityId

WINDOW = (1080, 720)


def test_health_depletion_is_bounded_and_deterministic():
    store = CombatStateStore()
    entity_id = EntityId(1)
    store.attach(entity_id, 100)

    first = store.deplete(entity_id, 35)
    second = store.deplete(entity_id, 500)

    assert first.health_lost == 35
    assert first.after == VitalState(65, 100)
    assert second.health_lost == 65
    assert second.after.health == 0
    assert second.after.depleted is True


def test_optional_armor_absorbs_before_health_and_restores_to_limits():
    store = CombatStateStore()
    entity_id = EntityId(2)
    store.attach(entity_id, 100, health=80, armor=25, max_armor=40)

    change = store.deplete(entity_id, 30)
    restored = store.restore(entity_id, health=50, armor=50)

    assert change.absorbed == 25
    assert change.health_lost == 5
    assert restored == VitalState(100, 100, 40, 40)


def test_combat_states_are_isolated_by_stable_entity_id():
    store = CombatStateStore()
    player = EntityId(1)
    enemy = EntityId(2)
    store.attach(player, 100)
    store.attach(enemy, 150)

    store.deplete(enemy, 20)

    assert store.get(player).health == 100
    assert store.get(enemy).health == 130


def test_invalid_arithmetic_and_duplicate_attachment_are_rejected():
    store = CombatStateStore()
    entity_id = EntityId(1)
    store.attach(entity_id, 100)

    with pytest.raises(ValueError):
        store.deplete(entity_id, -1)
    with pytest.raises(ValueError):
        store.restore(entity_id, health=-1)
    with pytest.raises(ValueError, match="already has combat state"):
        store.attach(entity_id, 100)


def test_session_bridges_player_and_enemy_health_by_id(display, cash):
    session = Session(Viewport(WINDOW))
    enemy = Zombie(WINDOW, cash)
    session.zombies.add(enemy)
    session._sync_enemy_registry()
    enemy_id = session.entities.id_for(enemy)

    session.human.health -= 12
    enemy.zombie_health -= 23
    session._sync_enemy_registry()
    session._sync_combat_state()

    assert session.combat.get(session.player_id).health == config.PLAYER_HEALTH - 12
    assert session.combat.get(enemy_id).health == config.ZOMBIE_HEALTH - 23

    enemy.kill()
    session._sync_enemy_registry()

    assert enemy_id not in session.combat
