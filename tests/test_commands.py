"""Characterize the first pygame-to-neutral command boundary."""

from dataclasses import asdict
import json

import pygame

from shooter import commands, config
from shooter.gameplay import GameplayScene
from shooter.input_adapter import PygameInputAdapter
from shooter.session import Session
from shooter.viewport import Viewport
from shooter.weapons import M16, SMG, equip

WINDOW = (1080, 720)


def pressed(*keys):
    return {key: key in keys for key in range(512)}


def test_sampled_controls_are_neutral_deterministic_and_serializable():
    adapter = PygameInputAdapter()

    first = adapter.sample(pressed(pygame.K_w, pygame.K_d), (800, 300), WINDOW, True)
    second = adapter.sample(pressed(pygame.K_w, pygame.K_d), (800, 300), WINDOW, True)

    assert first == second == commands.ControlFrame((1, -1), (260, 60), True)
    assert json.loads(json.dumps(asdict(first))) == {
        "move": [1, -1],
        "aim": [260, 60],
        "trigger_held": True,
    }


def test_discrete_actions_carry_only_neutral_values():
    adapter = PygameInputAdapter()

    reload_command = adapter.action_for(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)
    )
    slot_command = adapter.action_for(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3)
    )

    assert reload_command == commands.ActionCommand(commands.RELOAD)
    assert slot_command == commands.ActionCommand(commands.SELECT_SLOT, 2)
    assert json.dumps(asdict(slot_command))


def test_gameplay_moves_from_neutral_controls(display):
    scene = GameplayScene(Viewport(WINDOW))
    controls = PygameInputAdapter().sample(
        pressed(pygame.K_d), (800, 300), WINDOW
    )
    before = scene.session.camera

    scene.update(controls, config.SIM_DT)

    assert scene.session.camera_x < before[0]
    assert scene.session.aim == controls.aim


def test_gameplay_routes_reload_as_a_neutral_action(display):
    scene = GameplayScene(Viewport(WINDOW))
    scene.session.equipped = equip(M16)
    scene.session.carried.append(scene.session.equipped)
    scene.session.equipped.loaded -= 1

    scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))

    assert scene.session.equipped.locked_for > 0


def test_session_executes_essential_actions_without_pygame_events(display):
    session = Session(Viewport(WINDOW))
    rifle = equip(M16)
    smg = equip(SMG)
    session.carried = [rifle, smg]
    session.equipped = rifle
    session.aim = (100, 0)

    session.apply_action(commands.ActionCommand(commands.FIRE))
    session.apply_action(commands.ActionCommand(commands.SELECT_SLOT, 1))
    session.apply_action(commands.ActionCommand(commands.RELOAD))
    session.apply_action(commands.ActionCommand(commands.USE_GRENADE))
    session.apply_action(commands.ActionCommand(commands.USE_STUN_GRENADE))
    session.apply_action(commands.ActionCommand(commands.SKIP_PHASE))

    assert rifle.loaded == rifle.weapon.clip - 1
    assert session.equipped is smg
    assert smg.locked_for > 0
    assert len(session.grenades) == 1
    assert len(session.stun_grenades) == 1
    assert session.rules._skip_requested is True


def test_interaction_dispatches_without_a_key_code(display, monkeypatch):
    session = Session(Viewport(WINDOW))
    used = []
    monkeypatch.setattr(session, "_interact", lambda: used.append(True))

    session.apply_action(commands.ActionCommand(commands.INTERACT))

    assert used == [True]
