"""Small, presentation-independent counters carried by one player."""

from dataclasses import dataclass

from shooter import config


@dataclass(slots=True)
class EquipmentState:
    grenades: int = config.STARTING_GRENADES
    stun_grenades: int = config.STARTING_STUN_GRENADES

    # Temporary names retained for legacy gameplay callers. The state itself
    # no longer lives in the graphical HUD module.
    @property
    def grenade_amount(self):
        return self.grenades

    @grenade_amount.setter
    def grenade_amount(self, value):
        self.grenades = value

    @property
    def stun_grenade_amount(self):
        return self.stun_grenades

    @stun_grenade_amount.setter
    def stun_grenade_amount(self, value):
        self.stun_grenades = value
