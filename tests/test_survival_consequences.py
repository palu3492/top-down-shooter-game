"""Survival rewards and loot consume attributed facts, not actor side effects."""

from types import SimpleNamespace

from shooter import config
from shooter.domain_events import EntityKilled, EntityRemoved
from shooter.systems import loot, world
from shooter.systems.survival_consequences import SurvivalConsequences
from shooter.world_registry import EntityId, WorldRegistry


def test_only_attributed_player_kills_award_cash_and_loot(cash, monkeypatch):
    consequences = SurvivalConsequences()
    entities = WorldRegistry()
    player_id = EntityId(1)
    enemy = SimpleNamespace(kind="walker", get_position=lambda: (40, 60))
    enemy_id = entities.register(enemy, ("enemy",))
    spills = []
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))

    consequences.consume(
        (
            EntityKilled(enemy_id, player_id),
            EntityRemoved(enemy_id, "despawned"),
        ),
        player_id,
        entities,
        cash,
        lambda item, count, at: spills.append((item, count, at)),
    )

    assert cash.received == [config.KILL_REWARD]
    assert spills == [(world.CLOTH, 2, (40, 60))]


def test_despawns_and_kills_by_other_instigators_have_no_consequences(
    cash, monkeypatch
):
    consequences = SurvivalConsequences()
    entities = WorldRegistry()
    player_id = EntityId(1)
    other_id = EntityId(2)
    enemy = SimpleNamespace(kind="walker", get_position=lambda: (40, 60))
    enemy_id = entities.register(enemy, ("enemy",))
    spills = []
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))

    consequences.consume(
        (
            EntityRemoved(enemy_id, "despawned"),
            EntityKilled(enemy_id, other_id),
        ),
        player_id,
        entities,
        cash,
        lambda *drop: spills.append(drop),
    )

    assert cash.received == []
    assert spills == []


def test_zombie_has_no_wallet_dependency(window, cash):
    from shooter.entities.zombie import Zombie

    zombie = Zombie(window, cash)

    assert not hasattr(zombie, "player_cash")
