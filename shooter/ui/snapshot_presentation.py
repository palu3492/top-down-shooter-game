"""Small presentation host for any immutable Match snapshot."""

from shooter.presentation_status import SessionPresentationStatus
from shooter.ui.debug_overlay import DebugOverlay
from shooter.ui.equipment_overlay import EquipmentDebugOverlay
from shooter.ui.placeholder_world import PlaceholderWorldRenderer

EMPTY_PRESENTATION_STATUS = SessionPresentationStatus(0, 0, 0.0, ())


class SnapshotPresentation:
    def __init__(self, world=None, overlay=None):
        self.world = world or PlaceholderWorldRenderer()
        self.overlay = overlay or DebugOverlay()
        self.equipment_overlay = EquipmentDebugOverlay()

    def draw(
        self,
        surface,
        snapshot,
        camera=(0, 0),
        presentation=EMPTY_PRESENTATION_STATUS,
    ):
        self.world.draw(surface, snapshot, camera)
        self.overlay.draw(surface, snapshot, presentation)
        self.equipment_overlay.draw(surface, snapshot)
