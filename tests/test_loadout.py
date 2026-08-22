"""Owner-independent equipment slots and selection."""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from shooter.loadout import ActorInventory, Loadout, LoadoutFullError


def entry(name):
    return SimpleNamespace(name=name, runtime=SimpleNamespace(loaded=10))


def test_loadout_enforces_capacity_and_preserves_order():
    first, second, third = entry("first"), entry("second"), entry("third")
    loadout = Loadout((first, second), capacity=2)

    with pytest.raises(LoadoutFullError):
        loadout.add(third)

    assert tuple(loadout) == (first, second)


def test_selection_preserves_each_entries_runtime_state():
    first, second = entry("first"), entry("second")
    loadout = Loadout((first, second))
    first.runtime.loaded = 3

    assert loadout.select(1) is True
    assert loadout.selected is second
    assert loadout.select(0) is True
    assert loadout.selected is first
    assert loadout.selected.runtime.loaded == 3


def test_invalid_selection_does_not_replace_current_selection():
    first = entry("first")
    loadout = Loadout((first,))

    assert loadout.select(9) is False
    assert loadout.selected is first


def test_loadout_module_has_no_pygame_dependency():
    source = Path("shooter/loadout.py").read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    assert "pygame" not in imports


def test_actor_inventory_keeps_equipment_and_stackable_cargo_explicitly_separate():
    weapon = entry("rifle")
    pack = SimpleNamespace(stacks=[("wood", 2)])
    inventory = ActorInventory(Loadout((weapon,)), pack)

    assert inventory.loadout.selected is weapon
    assert inventory.backpack is pack
    assert inventory.loadout.selected.runtime.loaded == 10
