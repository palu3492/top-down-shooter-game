"""M8.4 removes graphical ownership without changing gameplay state."""

from pathlib import Path

from shooter.equipment_state import EquipmentState
from shooter.session import Session
from shooter.viewport import Viewport

WINDOW = (1080, 720)


def test_session_uses_neutral_cash_and_equipment_state(display):
    session = Session(Viewport(WINDOW))

    assert session.cash is session.survival_state.cash
    assert isinstance(session.grenade_data, EquipmentState)

    session.cash.cash_amount = 125
    grenades = session.grenade_data.grenades
    session.grenade_data.grenade_amount -= 1

    assert session.cash.balance == 125
    assert session.grenade_data.grenades == grenades - 1


def test_session_does_not_import_retired_graphical_hud_modules():
    source = Path("shooter/session.py").read_text()

    for module in (
        "shooter.ui.hud",
        "shooter.ui.radar",
        "shooter.ui.shopfront",
        "shooter.ui.mode_status",
    ):
        assert module not in source
