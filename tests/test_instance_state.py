"""State must live on the instance, not be inherited from the class body.

Before AT7 the isolation tests elsewhere passed by accident: `+=` on an int
rebinds to the instance, so a freshly built object simply read the class
attribute and looked correct until something mutated it. These assert the
stronger property -- the state exists on the instance from construction.
"""

import ast
import pathlib

import pygame
import pytest

from shooter.entities.player import Human
from shooter.entities.powerups import PowerUps
from shooter.entities.projectiles import (
    Grenade,
    GrenadeDetonation,
    Shot,
    StunDetonation,
    StunGrenade,
)
from shooter.entities.zombie import Zombie
from shooter.systems.waves import WaveSystem
from shooter.ui.hud import Cash, GrenadeData, GunData

MUTABLE = {
    "Cash": ["cash_amount"],
    "GunData": ["clip_size", "ammo_amount", "reload_seconds"],
    "GrenadeData": ["grenade_amount", "stun_grenade_amount"],
    "WaveSystem": ["wave_count", "wave_seconds"],
    "PowerUps": ["powerup_selected", "alive_seconds"],
    "Human": ["health", "current_idle", "current_move", "current_shoot", "type"],
    "Zombie": ["zombie_health", "zombie_speed", "stun_seconds", "zombie_x", "zombie_y"],
    "Shot": ["kill_me", "bullet_x", "bullet_y", "damage"],
    "Grenade": ["explode", "grenade_x", "grenade_y", "travelled", "flight"],
    "StunGrenade": ["explode", "grenade_x", "grenade_y"],
    "GrenadeDetonation": ["life", "explosion_x", "explosion_y"],
    "StunDetonation": ["life", "explosion_x", "explosion_y"],
}


@pytest.fixture
def built(window, cash):
    group = pygame.sprite.Group()
    return {
        "Cash": Cash(),
        "GunData": GunData(window),
        "GrenadeData": GrenadeData(),
        "WaveSystem": WaveSystem(window, group, cash),
        "PowerUps": PowerUps(),
        "Human": Human(window),
        "Zombie": Zombie(window, cash),
        "Shot": Shot(0, 0, 1, 1),
        "Grenade": Grenade(0, 0, 1, 1),
        "StunGrenade": StunGrenade(0, 0, 1, 1),
        "GrenadeDetonation": GrenadeDetonation(0, 0),
        "StunDetonation": StunDetonation(0, 0),
    }


@pytest.mark.parametrize("name", sorted(MUTABLE))
def test_mutable_state_is_set_on_the_instance(built, name):
    obj = built[name]
    missing = [attr for attr in MUTABLE[name] if attr not in vars(obj)]

    assert missing == []


def test_no_class_body_still_declares_mutable_state():
    """Only ALL_CAPS constants may live on a class body."""
    offenders = []
    for path in pathlib.Path("shooter").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ClassDef):
                continue
            for body in node.body:
                if not isinstance(body, ast.Assign):
                    continue
                for target in body.targets:
                    if isinstance(target, ast.Name) and not target.id.isupper():
                        offenders.append(f"{node.name}.{target.id}")

    assert offenders == []


def test_two_wallets_do_not_share_a_balance_even_before_a_write():
    a, b = Cash(), Cash()

    assert "cash_amount" in vars(a)
    assert "cash_amount" in vars(b)
    assert a.cash_amount is not None


def test_mutating_one_instance_never_touches_the_class(window, cash):
    zombie = Zombie(window, cash)
    zombie.remove_health(40)
    zombie.remove_speed(1)

    assert Zombie(window, cash).zombie_health == 100.0
    assert not hasattr(Zombie, "zombie_health")
    assert not hasattr(Zombie, "zombie_speed")
