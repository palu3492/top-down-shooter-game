"""What the player can carry, and what carries it.

One primitive serves both halves of the plan: a weapon is an item you equip,
wood is an item you stack, and ammunition is an item that competes with both for
room. Building the container once means loot, harvesting and the armoury are all
the same thing afterwards.

There is no display here and nothing uses it yet -- this is the AT23 shape. The
hard part is the rules, and bundling them with a screen would hide them behind
UI review.
"""

from dataclasses import dataclass

WEAPON = "weapon"
AMMO = "ammo"
RESOURCE = "resource"
TOOL = "tool"

KINDS = (WEAPON, AMMO, RESOURCE, TOOL)

SLOTS = 12
MOST_SLOTS = 40


class UnknownItemError(KeyError):
    """An item id nothing has been registered under."""


@dataclass(frozen=True)
class Item:
    """A thing that can be carried.

    `stack` is how many fit in one slot. A weapon is one per slot, so carrying a
    second shotgun costs what a hundred rounds would; that is the trade the
    backpack exists to make.
    """

    id: str
    name: str
    kind: str
    stack: int = 1

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"{self.id} has no kind {self.kind!r}")
        if self.stack < 1:
            raise ValueError(f"{self.id} must fit at least once in a slot")


CATALOGUE = {}


def register(*items):
    """Make items known. Returns them, so a module can define and register in
    one breath."""
    for item in items:
        CATALOGUE[item.id] = item
    return items[0] if len(items) == 1 else items


def item(item_id):
    if item_id not in CATALOGUE:
        raise UnknownItemError(item_id)
    return CATALOGUE[item_id]


def of_kind(kind):
    return tuple(found for found in CATALOGUE.values() if found.kind == kind)


@dataclass
class Stack:
    """One slot's worth: an item and how many of it."""

    item: Item
    count: int

    @property
    def room(self):
        return self.item.stack - self.count

    @property
    def full(self):
        return self.room <= 0


def sane_slots(slots, at_least=1):
    """What counts as a slot number, decided once.

    The constructor and `resize` were disagreeing about it: one clamped to the
    upper limit and the other did not.
    """
    return max(max(1, at_least), min(int(slots), MOST_SLOTS))


class Backpack:
    """A fixed number of slots, and what is in them.

    Adding what will not fit takes what it can and reports how much. A pack that
    silently swallows everything makes looting a formality; one that fills up
    makes it a decision, and gives a better backpack something to be worth.
    """

    def __init__(self, slots=SLOTS):
        self.slots = sane_slots(slots)
        self.stacks = []

    def __len__(self):
        return len(self.stacks)

    def __iter__(self):
        return iter(self.stacks)

    def __contains__(self, thing):
        return self.count(thing) > 0

    @property
    def full(self):
        return len(self.stacks) >= self.slots and all(
            stack.full for stack in self.stacks
        )

    @property
    def free_slots(self):
        return self.slots - len(self.stacks)

    def count(self, thing):
        wanted = self._resolve(thing)
        return sum(stack.count for stack in self.stacks if stack.item is wanted)

    def has(self, thing, count=1):
        return self.count(thing) >= count

    def room_for(self, thing):
        """How many more of this would fit, across part-used and empty slots."""
        wanted = self._resolve(thing)
        spare = sum(
            stack.room
            for stack in self.stacks
            if stack.item is wanted and not stack.full
        )
        return spare + self.free_slots * wanted.stack

    def add(self, thing, count=1):
        """Take what fits; return how many were taken.

        Part-used slots are filled before empty ones, so a pack does not end up
        with three half-stacks of the same thing.
        """
        wanted = self._resolve(thing)
        if count <= 0:
            return 0
        taken = 0

        for stack in self.stacks:
            if taken == count:
                break
            if stack.item is not wanted or stack.full:
                continue
            room = min(stack.room, count - taken)
            stack.count += room
            taken += room

        while taken < count and self.free_slots > 0:
            room = min(wanted.stack, count - taken)
            self.stacks.append(Stack(wanted, room))
            taken += room

        return taken

    def remove(self, thing, count=1):
        """Give up what is there; return how many were given.

        Part-used slots go first, so a pack empties into whole stacks rather
        than a scattering of remainders.
        """
        wanted = self._resolve(thing)
        if count <= 0:
            return 0
        given = 0

        for stack in sorted(self._holding(wanted), key=lambda s: s.count):
            if given == count:
                break
            gone = min(stack.count, count - given)
            stack.count -= gone
            given += gone

        self.stacks = [stack for stack in self.stacks if stack.count > 0]
        return given

    def resize(self, slots):
        """A better backpack. Never smaller than what is already in it, because
        there is nowhere for the overflow to go."""
        self.slots = sane_slots(slots, at_least=len(self.stacks))
        return self.slots

    def _holding(self, wanted):
        return [stack for stack in self.stacks if stack.item is wanted]

    def _resolve(self, thing):
        return thing if isinstance(thing, Item) else item(thing)
