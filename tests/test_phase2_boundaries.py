"""Executable exit checks for neutral commands, IDs, and domain facts."""

from pathlib import Path

from shooter import commands, config
from shooter.domain_events import EntityRegistered, EntityRemoved
from shooter.entities.zombie import Zombie
from shooter.session import Session
from shooter.viewport import Viewport

ROOT = Path(__file__).parents[1]
WINDOW = (1080, 720)


def test_neutral_phase2_modules_do_not_depend_on_pygame():
    for relative in (
        "shooter/commands.py",
        "shooter/domain_events.py",
        "shooter/world_registry.py",
    ):
        source = (ROOT / relative).read_text()
        assert "import pygame" not in source
        assert "from pygame" not in source


def test_simulation_and_rules_do_not_poll_pygame_input():
    for relative in ("shooter/session.py", "shooter/systems/waves.py"):
        source = (ROOT / relative).read_text()
        assert "pygame.key.get_pressed" not in source
        assert "pygame.mouse.get_pressed" not in source


def test_commands_ids_and_lifecycle_facts_cross_one_match_seam(display, cash):
    session = Session(Viewport(WINDOW))
    session.events.drain()
    before = session.camera

    session.step_controls(commands.ControlFrame(move=(1, 0), aim=(120, 10)))
    session.apply_action(commands.ActionCommand(commands.SKIP_PHASE))
    enemy = Zombie(WINDOW, cash)
    session.zombies.add(enemy)
    session._sync_enemy_registry()
    enemy_id = session.entities.id_for(enemy)

    assert session.camera_x == before[0] - config.PLAYER_SPEED * config.SIM_DT
    assert session.aim == (120, 10)
    assert session.rules._skip_requested is True
    assert session.events.drain() == (
        EntityRegistered(enemy_id, ("actor", "enemy")),
    )

    enemy.kill()
    session._sync_enemy_registry()

    assert session.events.drain() == (
        EntityRemoved(enemy_id, "legacy_group_removal"),
    )
