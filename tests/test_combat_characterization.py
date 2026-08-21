"""Observable legacy combat consequences protected during the migration."""

import pygame

from shooter import config
from shooter.entities import powerups
from shooter.entities.zombie import Zombie
from shooter.session import Session
from shooter.systems import loot, world
from shooter.viewport import Viewport
from shooter.weapons import M16, equip

WINDOW = (1080, 720)


def armed_session():
    session = Session(Viewport(WINDOW))
    session.carried = [equip(M16)]
    session.equipped = session.carried[0]
    session.aim_at((WINDOW[0] / 2 + 100, WINDOW[1] / 2))
    return session


def target_in_front(session, health):
    target = Zombie(WINDOW, session.cash)
    target.zombie_speed = 0
    target.zombie_health = health
    muzzle_x, muzzle_y = session._muzzle()
    target.set_position(muzzle_x + 60, muzzle_y)
    session.zombies.add(target)
    return target


def fire(session):
    session.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))


def test_fire_through_reward_and_loot_is_one_observable_path(
    input_frame, monkeypatch
):
    session = armed_session()
    target = target_in_front(session, session.equipped.damage)
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))
    loaded = session.equipped.loaded

    fire(session)

    assert session.equipped.loaded == loaded - 1
    assert len(session.bullets) == 1

    session.step(input_frame().pressed)

    assert target not in session.zombies
    assert target.killed is True
    assert session.cash.cash_amount == config.KILL_REWARD
    assert len(session.dropped) == 1
    pile = next(iter(session.dropped))
    assert (pile.item, pile.count) == (world.CLOTH, 2)

    session.step(input_frame().pressed)

    assert session.cash.cash_amount == config.KILL_REWARD
    dropped_cloth = sum(
        dropped.count for dropped in session.dropped if dropped.item is world.CLOTH
    )
    assert session.backpack.count(world.CLOTH) + dropped_cloth == 2


def test_a_nonlethal_hit_neither_removes_nor_rewards(input_frame, monkeypatch):
    session = armed_session()
    target = target_in_front(session, session.equipped.damage + 1)
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))

    fire(session)
    session.step(input_frame().pressed)

    assert target in session.zombies
    assert target.killed is False
    assert target.zombie_health == 1
    assert session.cash.cash_amount == 0
    assert len(session.dropped) == 0


def test_a_non_kill_removal_has_no_reward_or_loot(input_frame, monkeypatch):
    session = armed_session()
    target = target_in_front(session, session.equipped.damage)
    monkeypatch.setattr(loot, "spoils", lambda kind: ((world.CLOTH, 2),))
    pickup = next(iter(session.powerups))
    monkeypatch.setattr(
        pickup,
        "update",
        lambda *args, **kwargs: powerups.NUKE,
        raising=False,
    )

    session.step(input_frame().pressed)

    assert target not in session.zombies
    assert target.killed is False
    assert session.cash.cash_amount == 0
    assert len(session.dropped) == 0
