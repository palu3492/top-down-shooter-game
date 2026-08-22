"""Owner-independent equipment slots and actor inventory boundaries."""

from dataclasses import dataclass


class LoadoutFullError(ValueError):
    pass


class Loadout:
    def __init__(self, entries=(), capacity=5, selected=0):
        self.capacity = capacity
        self._entries = list(entries)
        if len(self._entries) > capacity:
            raise LoadoutFullError(capacity)
        self._selected = selected if self._entries else None
        self._normalize_selection()

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    @property
    def full(self):
        return len(self) >= self.capacity

    @property
    def selected_index(self):
        self._normalize_selection()
        return self._selected

    @property
    def selected(self):
        self._normalize_selection()
        return None if self._selected is None else self._entries[self._selected]

    def add(self, entry, *, select=False):
        if self.full:
            raise LoadoutFullError(self.capacity)
        self._entries.append(entry)
        if self._selected is None or select:
            self._selected = len(self._entries) - 1
        return entry

    def select(self, slot):
        if slot < 0 or slot >= len(self._entries):
            return False
        self._selected = slot
        return True

    def select_entry(self, entry):
        for slot, candidate in enumerate(self._entries):
            if candidate is entry:
                self._selected = slot
                return True
        return False

    def find(self, predicate):
        return next((entry for entry in self._entries if predicate(entry)), None)

    def replace(self, entries, selected=0):
        entries = list(entries)
        if len(entries) > self.capacity:
            raise LoadoutFullError(self.capacity)
        self._entries[:] = entries
        self._selected = selected if entries else None
        self._normalize_selection()

    def compatibility_entries(self):
        """Temporary mutable view for legacy callers during Session migration."""
        return self._entries

    def _normalize_selection(self):
        if not self._entries:
            self._selected = None
        elif self._selected is None or self._selected >= len(self._entries):
            self._selected = 0


@dataclass(slots=True)
class ActorInventory:
    """Equipment is operated in a loadout; stackable cargo stays in a pack.

    Ammunition already loaded or reserved by a weapon remains in that weapon's
    runtime state. It is not duplicated as backpack cargo.
    """

    loadout: Loadout
    backpack: object
