"""Legacy command and match-lifecycle outcomes protected during migration."""

import pygame

from shooter import config
from shooter.entities.projectiles import Shot
from shooter.entities.zombie import Zombie
from shooter.gameplay import GameplayScene
from shooter.session import Session, WON
from shooter.viewport import Viewport
from shooter.weapons import M16, RELOAD, SMG, equip

WINDOW = (1080, 720)


def test_dead_and_despawned_targets_cannot_pay_again(cash):
    killed = Zombie(WINDOW, cash)
    killed.zombie_health = 1

    assert killed.remove_health(1) is True
    assert killed.remove_health(1) is False

    despawned = Zombie(WINDOW, cash)
    despawned.kill()
    shot = Shot(0, 0, 1, 0, damage=10_000)
    shot.update(0, 0, pygame.sprite.Group())

    assert cash.received == [config.KILL_REWARD]
    assert despawned.killed is False


def test_weapon_state_survives_gameplay_input_cooldown_reload_and_swap(
    input_frame, advance_steps
):
    session = Session(Viewport(WINDOW))
    smg = equip(SMG)
    rifle = equip(M16)
    session.carried = [smg, rifle]
    session.equipped = smg
    session.aim_at((WINDOW[0] / 2 + 100, WINDOW[1] / 2))
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)

    session.handle(click)
    after_first = smg.loaded
    session.handle(click)

    assert smg.loaded == after_first

    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    assert smg.status == RELOAD
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))

    advance_steps(
        lambda dt: session.step(input_frame().pressed, dt),
        int(smg.weapon.reload_seconds / config.SIM_DT) + 1,
    )
    session.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))

    assert session.equipped is smg
    assert smg.loaded == smg.weapon.clip
    assert smg.status is None


def test_consecutive_sessions_share_no_match_scoped_state():
    first = Session(Viewport(WINDOW))
    first.cash.increase_cash(900)
    first.rules.wave_count = 7
    first.rules.wave_seconds = 3.0
    first.equipped.cooling_for = 2.0
    first.bullets.add(Shot(0, 0, 1, 0))

    second = Session(Viewport(WINDOW))

    assert second is not first
    assert second.cash.cash_amount == 0
    assert second.rules.wave_count == 0
    assert second.rules.wave_seconds == 0.0
    assert second.equipped.cooling_for == 0.0
    assert not second.bullets
    assert second.zombies is not first.zombies
    assert second.powerups is not first.powerups


def test_outcome_is_reported_once_and_a_fresh_match_can_follow(display):
    class FinishedRules:
        outcome = WON
        level = None
        layout = ()

        def __init__(self, *args):
            pass

    first = GameplayScene(Viewport(WINDOW), rules=FinishedRules)

    assert first.tick(0.0) == WON
    assert first.tick(0.0) is None

    second = GameplayScene(Viewport(WINDOW), rules=FinishedRules)

    assert second is not first
    assert second.session is not first.session
    assert second.reported is False
    assert second.tick(0.0) == WON
