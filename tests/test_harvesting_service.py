"""Map harvestables use tool capabilities without a mode or pygame dependency."""

from shooter.harvesting import (
    DEPLETED,
    HARVESTED,
    INCOMPATIBLE_TOOL,
    HarvestingService,
)
from shooter.map_definition import MapHarvestable
from shooter.weapon_state import EquippedWeapon, WeaponDefinition

PICKAXE = EquippedWeapon(
    WeaponDefinition(
        "pickaxe", "melee", 30, 1, reach=80, capabilities=frozenset(("harvest",))
    )
)
KNIFE = EquippedWeapon(WeaponDefinition("knife", "melee", 30, 1, reach=80))


def test_harvesting_applies_tool_damage_to_authored_durability_only():
    definition = MapHarvestable(
        "tree-1", "tree", position=(20, 0), properties=(("durability", "50"),)
    )
    states = HarvestingService().create_states((definition,))

    first = HarvestingService().harvest(PICKAXE, states["tree-1"])
    second = HarvestingService().harvest(PICKAXE, states["tree-1"])
    third = HarvestingService().harvest(PICKAXE, states["tree-1"])

    assert (first.reason, first.remaining_durability) == (HARVESTED, 20)
    assert (second.reason, second.remaining_durability) == (HARVESTED, 0)
    assert third.reason == DEPLETED


def test_harvesting_requires_the_authored_tool_capability():
    definition = MapHarvestable(
        "tree-1", "tree", position=(20, 0), properties=(("durability", "50"),)
    )
    state = HarvestingService().create_states((definition,))["tree-1"]

    result = HarvestingService().harvest(KNIFE, state)

    assert result.reason == INCOMPATIBLE_TOOL
    assert state.durability == 50


def test_nearby_harvestable_exposes_a_tool_specific_prompt():
    definition = MapHarvestable(
        "truck-1",
        "vehicle",
        position=(20, 0),
        properties=(("durability", "50"), ("resource_id", "metal")),
    )
    states = HarvestingService().create_states((definition,))

    context = HarvestingService().discover(states, (0, 0), 80, PICKAXE)

    assert context.prompt == "PRESS Q: HARVEST VEHICLE FOR METAL"


def test_harvest_yields_are_deterministic_across_multiple_tool_hits():
    definition = MapHarvestable(
        "truck-1",
        "vehicle",
        position=(20, 0),
        properties=(
            ("durability", "100"),
            ("resource_id", "metal"),
            ("resource_yield", "7"),
        ),
    )
    state = HarvestingService().create_states((definition,))["truck-1"]

    first = HarvestingService().harvest(PICKAXE, state)
    second = HarvestingService().harvest(PICKAXE, state)
    third = HarvestingService().harvest(PICKAXE, state)
    fourth = HarvestingService().harvest(PICKAXE, state)

    amounts = [result.resource_amount for result in (first, second, third, fourth)]
    assert amounts == [2, 2, 2, 1]
    assert sum(result.resource_amount for result in (first, second, third, fourth)) == 7
