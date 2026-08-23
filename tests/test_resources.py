"""Match resources are transaction values, not cash or backpack presentation state."""

import pytest

from shooter.resources import ResourceInventory


def test_resources_track_independent_quantities_and_transactional_spending():
    inventory = ResourceInventory((("wood", 5), ("metal", 2)))

    inventory.add("wood", 4)

    assert inventory.snapshot() == (("metal", 2), ("wood", 9))
    assert inventory.spend("wood", 10) is False
    assert inventory.spend("wood", 6) is True
    assert inventory.snapshot() == (("metal", 2), ("wood", 3))


def test_resources_reject_invalid_mutations():
    inventory = ResourceInventory()

    with pytest.raises(ValueError):
        inventory.add("", 1)
    with pytest.raises(ValueError):
        inventory.add("wood", -1)
    with pytest.raises(ValueError):
        inventory.spend("wood", -1)
