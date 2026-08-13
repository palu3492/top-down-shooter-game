"""Items and the backpack.

Pure rules with no display behind them, so the interesting cases can be
enumerated rather than sampled. The one that matters is what happens when
something does not fit: a pack that quietly swallows everything makes looting a
formality, and every caller downstream would be written believing `add` always
succeeds.
"""

import pytest

from shooter import items
from shooter.items import AMMO, RESOURCE, WEAPON, Backpack, Item

KNIFE = Item("test_knife", "Knife", WEAPON)
SHOTGUN = Item("test_shotgun", "Shotgun", WEAPON)
SHELLS = Item("test_shells", "Shells", AMMO, stack=40)
WOOD = Item("test_wood", "Wood", RESOURCE, stack=25)


@pytest.fixture(autouse=True)
def catalogue():
    """Registered per test, so one test's items cannot leak into another."""
    before = dict(items.CATALOGUE)
    items.register(KNIFE, SHOTGUN, SHELLS, WOOD)
    yield items.CATALOGUE
    items.CATALOGUE.clear()
    items.CATALOGUE.update(before)


@pytest.fixture
def pack():
    return Backpack(slots=4)


# ----------------------------------------------------------------------
# Items
# ----------------------------------------------------------------------


def test_an_item_needs_a_kind_that_exists():
    with pytest.raises(ValueError):
        Item("odd", "Odd", "vegetable")


def test_an_item_must_fit_in_a_slot_at_least_once():
    with pytest.raises(ValueError):
        Item("nothing", "Nothing", RESOURCE, stack=0)


def test_items_can_be_looked_up_by_id():
    assert items.item("test_shells") is SHELLS


def test_an_unknown_id_is_refused_rather_than_invented():
    with pytest.raises(items.UnknownItemError):
        items.item("test_rocket_launcher")


def test_items_can_be_found_by_kind():
    assert set(items.of_kind(WEAPON)) >= {KNIFE, SHOTGUN}
    assert SHELLS not in items.of_kind(WEAPON)


# ----------------------------------------------------------------------
# Carrying things
# ----------------------------------------------------------------------


def test_a_new_pack_is_empty(pack):
    assert len(pack) == 0
    assert pack.count(WOOD) == 0
    assert WOOD not in pack


def test_adding_something_puts_it_there(pack):
    assert pack.add(WOOD, 5) == 5
    assert pack.count(WOOD) == 5
    assert WOOD in pack


def test_things_can_be_asked_for_by_id(pack):
    pack.add("test_wood", 3)
    assert pack.count("test_wood") == 3


def test_a_stack_fills_before_a_new_slot_is_opened(pack):
    pack.add(WOOD, 10)
    pack.add(WOOD, 10)

    assert len(pack) == 1, "a pack should not hold two half-stacks of one thing"
    assert pack.count(WOOD) == 20


def test_more_than_a_stack_spills_into_the_next_slot(pack):
    pack.add(WOOD, 30)

    assert len(pack) == 2
    assert pack.count(WOOD) == 30


def test_a_weapon_costs_a_whole_slot(pack):
    """One per slot, so a second shotgun costs what twenty-five wood would."""
    pack.add(SHOTGUN, 1)
    pack.add(SHOTGUN, 1)

    assert len(pack) == 2
    assert pack.count(SHOTGUN) == 2


# ----------------------------------------------------------------------
# Not fitting
# ----------------------------------------------------------------------


def test_a_full_pack_takes_what_it_can_and_says_how_much(pack):
    """The whole point. Looting is a decision only if it can fail."""
    taken = pack.add(WOOD, 500)

    assert taken == 4 * 25, "four slots of twenty-five"
    assert pack.count(WOOD) == 100
    assert pack.full is True


def test_what_would_not_fit_is_not_quietly_swallowed(pack):
    pack.add(WOOD, 500)
    assert pack.add(WOOD, 10) == 0
    assert pack.count(WOOD) == 100


def test_a_pack_with_a_part_used_stack_is_not_full(pack):
    pack.add(WOOD, 4 * 25 - 1)
    assert pack.full is False
    assert pack.add(WOOD, 5) == 1


def test_room_for_counts_part_used_and_empty_slots(pack):
    pack.add(WOOD, 30)  # one full stack, one holding five

    assert pack.free_slots == 2
    assert pack.room_for(WOOD) == 20 + 2 * 25


def test_room_for_something_not_carried_is_the_empty_slots(pack):
    pack.add(WOOD, 25)
    assert pack.room_for(SHELLS) == 3 * 40


def test_adding_nothing_takes_nothing(pack):
    assert pack.add(WOOD, 0) == 0
    assert pack.add(WOOD, -5) == 0
    assert len(pack) == 0


# ----------------------------------------------------------------------
# Giving things up
# ----------------------------------------------------------------------


def test_removing_gives_back_what_was_there(pack):
    pack.add(WOOD, 10)
    assert pack.remove(WOOD, 4) == 4
    assert pack.count(WOOD) == 6


def test_removing_more_than_is_carried_gives_what_there_is(pack):
    pack.add(WOOD, 3)
    assert pack.remove(WOOD, 10) == 3
    assert pack.count(WOOD) == 0


def test_an_emptied_slot_is_given_back(pack):
    pack.add(WOOD, 10)
    pack.remove(WOOD, 10)

    assert len(pack) == 0
    assert pack.free_slots == 4


def test_removing_empties_part_used_stacks_first(pack):
    """So a pack empties into whole stacks rather than a scattering of
    remainders that each cost a slot."""
    pack.add(WOOD, 30)  # 25 and 5
    pack.remove(WOOD, 5)

    assert len(pack) == 1
    assert pack.count(WOOD) == 25


def test_removing_what_is_not_there_takes_nothing(pack):
    pack.add(WOOD, 5)
    assert pack.remove(SHELLS, 3) == 0
    assert pack.count(WOOD) == 5


def test_has_answers_whether_there_is_enough(pack):
    pack.add(SHELLS, 12)
    assert pack.has(SHELLS, 12) is True
    assert pack.has(SHELLS, 13) is False
    assert pack.has(WOOD) is False


# ----------------------------------------------------------------------
# A better backpack
# ----------------------------------------------------------------------


def test_a_bigger_pack_holds_more(pack):
    pack.add(WOOD, 500)
    assert pack.full is True

    pack.resize(8)

    assert pack.full is False
    assert pack.add(WOOD, 500) == 4 * 25


def test_a_pack_cannot_shrink_below_what_is_in_it(pack):
    """There would be nowhere for the overflow to go."""
    pack.add(WOOD, 30)
    pack.add(SHELLS, 1)

    assert pack.resize(1) == 3
    assert pack.count(WOOD) == 30
    assert pack.count(SHELLS) == 1


def test_a_pack_has_an_upper_limit():
    assert Backpack(slots=10_000).slots == items.MOST_SLOTS


def test_a_pack_always_has_at_least_one_slot():
    assert Backpack(slots=0).slots == 1
    assert Backpack(slots=-4).slots == 1


# ----------------------------------------------------------------------
# Two arcs, one container
# ----------------------------------------------------------------------


def test_weapons_ammunition_and_resources_share_the_room(pack):
    """The trade the backpack exists to make: carrying a second gun costs the
    space its ammunition would have taken."""
    pack.add(SHOTGUN, 1)
    pack.add(SHELLS, 40)
    pack.add(WOOD, 25)

    assert pack.free_slots == 1
    assert pack.add(SHOTGUN, 1) == 1
    assert pack.full is True
    assert pack.add(SHELLS, 1) == 0
