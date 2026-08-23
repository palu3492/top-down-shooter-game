"""Match-owned, stack-free resource quantities for gameplay transactions."""


class ResourceInventory:
    def __init__(self, quantities=()):
        self._quantities = {}
        for resource_id, amount in quantities:
            self.add(resource_id, amount)

    def count(self, resource_id):
        return self._quantities.get(resource_id, 0)

    def add(self, resource_id, amount):
        if not resource_id:
            raise ValueError("resource_id is required")
        if amount < 0:
            raise ValueError("resource additions cannot be negative")
        self._quantities[resource_id] = self.count(resource_id) + int(amount)
        return self.count(resource_id)

    def spend(self, resource_id, amount):
        if amount < 0:
            raise ValueError("resource spending cannot be negative")
        if self.count(resource_id) < amount:
            return False
        self._quantities[resource_id] = self.count(resource_id) - int(amount)
        return True

    def snapshot(self):
        return tuple(sorted(self._quantities.items()))
