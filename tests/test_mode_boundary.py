"""Zombie Survival is a Match-hosted policy package, not the shared engine."""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pygame
import pytest

from shooter.modes.zombie_survival import SurvivalConsequences, WaveSystem
from shooter.modes.zombie_survival import shop
from shooter.modes.zombie_survival.state import SurvivalState, SurvivalWallet
from shooter.systems.survival_consequences import (
    SurvivalConsequences as LegacyConsequences,
)
from shooter.systems.waves import WaveSystem as LegacyWaves


def direct_imports(filename):
    imports = set()
    for node in ast.walk(ast.parse(Path(filename).read_text())):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_mode_contract_is_pygame_free_and_intentionally_small():
    source = Path("shooter/modes/contract.py").read_text()
    tree = ast.parse(source)
    methods = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert methods == {"start", "advance", "status", "result", "dispose"}
    roots = {
        name.split(".")[0] for name in direct_imports("shooter/modes/contract.py")
    }
    assert "pygame" not in roots


def test_survival_policy_has_moved_behind_mode_package_compatibility_imports():
    assert LegacyWaves is WaveSystem
    assert LegacyConsequences is SurvivalConsequences
    assert shop.STOCK


def test_survival_cash_and_outcome_are_mode_owned_and_headless():
    state = SurvivalState()
    assert isinstance(state.cash, SurvivalWallet)
    assert state.cash.cash_add_remove(-1) is False
    state.cash.increase_cash(100)
    assert state.cash.cash_add_remove(-40) is True
    assert state.cash.balance == 60
    assert state.outcome(True, "WON") == "WON"
    assert state.outcome(False, "WON") == "LOST"
    assert "pygame" not in {
        name.split(".")[0]
        for name in direct_imports("shooter/modes/zombie_survival/state.py")
    }


def test_shared_economy_does_not_import_a_game_mode():
    assert not any(
        name.startswith("shooter.modes")
        for name in direct_imports("shooter/economy.py")
    )


def test_survival_rules_expose_immutable_status_without_rendering_dependencies(
    window, cash
):
    rules = WaveSystem(window, pygame.sprite.Group(), cash)
    status = rules.status(cash=75, enemies_remaining=3)

    assert status.phase == "combat"
    assert status.cash == 75
    assert status.enemies_remaining == 3
    with pytest.raises(FrozenInstanceError):
        status.wave = 99

    imports = direct_imports("shooter/modes/zombie_survival/waves.py")
    assert "pygame" not in imports
    assert not any(name.startswith("shooter.ui") for name in imports)
