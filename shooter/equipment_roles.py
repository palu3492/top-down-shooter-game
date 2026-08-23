"""Optional equipment roles that are intentionally separate from firearm slots."""


class ToolSlot:
    """One mode-configured tool/melee role, or an explicit absence of one."""

    def __init__(self, equipped=None):
        self._equipped = equipped

    @property
    def equipped(self):
        return self._equipped

    @property
    def configured(self):
        return self._equipped is not None

    def configure(self, equipped):
        self._equipped = equipped
        return equipped
