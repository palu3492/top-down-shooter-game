"""Legacy attack adapters route consequences through the shared service."""

from types import SimpleNamespace

import pytest

from shooter import config
from shooter.domain_events import EntityRemoved
from shooter.entities.zombie import Zombie
from shooter.session import Session
from shooter.systems import loot, world
from shooter.viewport import Viewport

WINDOW = (1080, 720)


@pytest.fixture
def routed(display, cash):
    session = Session(Viewport(WINDOW))
    enemy = Zombie(WINDOW, cash)
    session.zombies.add(enemy)
    session._sync_enemy_registry()
    return session, enemy


def attack(session, weapon_id="test_weapon"):
    return SimpleNamespace(
        instigator_id=session.player_id,
        weapon_id=weapon_id,
    )


@pytest.mark.parametrize("damage_type", ("ballistic", "melee", "explosive"))
def test_shared_player_attack_types_mutate_combat_state_then_actor(routed, damage_type):
    session, enemy = routed
    enemy_id = session.entities.id_for(enemy)

    result = session._apply_attack_damage(
        attack(session), enemy, 15, damage_type
    )

    assert result.request.instigator_id == session.player_id
    assert result.request.target_id == enemy_id
    assert result.request.damage_type == damage_type
    assert result.request.weapon_id == "test_weapon"
    assert session.combat.get(enemy_id).health == config.ZOMBIE_HEALTH - 15
    assert enemy.zombie_health == session.combat.get(enemy_id).health


def test_contact_damage_routes_from_enemy_id_to_player_id(routed):
    session, enemy = routed
    enemy_id = session.entities.id_for(enemy)

    result = session._apply_contact_damage(enemy, 12)

    assert result.request.instigator_id == enemy_id
    assert result.request.target_id == session.player_id
    assert result.request.damage_type == "contact"
    assert session.combat.get(session.player_id).health == config.PLAYER_HEALTH - 12
    assert session.human.health == session.combat.get(session.player_id).health


def test_relationship_policy_rejects_a_routed_friendly_hit(routed):
    session, enemy = routed
    enemy_id = session.entities.id_for(enemy)
    session.factions.assign(enemy_id, "survivors")

    result = session._apply_attack_damage(
        attack(session), enemy, 1000, "ballistic"
    )

    assert result.applied is False
    assert session.combat.get(enemy_id).health == config.ZOMBIE_HEALTH
    assert enemy.zombie_health == config.ZOMBIE_HEALTH


def test_attributed_kill_flows_through_reward_loot_and_removal(routed, monkeypatch):
    session, enemy = routed
    enemy_id = session.entities.id_for(enemy)
    before_cash = session.cash.cash_amount
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))

    result = session._apply_attack_damage(
        attack(session), enemy, config.ZOMBIE_HEALTH, "ballistic"
    )
    session._consume_survival_events()
    session._sync_enemy_registry()

    assert result.lethal is True
    assert session.cash.cash_amount == before_cash + config.KILL_REWARD
    assert len(session.dropped) == 1
    assert enemy_id not in session.entities
    assert session.events.drain() == (EntityRemoved(enemy_id, "killed"),)
