"""Bottom-right text diagnostics for the active tool and firearms."""

import pygame

from shooter.ui.debug_overlay import BACKGROUND, BORDER, INSET, MUTED, TEXT


class EquipmentDebugOverlay:
    def lines(self, snapshot):
        player = next(
            (entity for entity in snapshot.entities if "player" in entity.tags), None
        )
        if player is None:
            return ("EQUIPMENT -",)
        weapons = tuple(player.weapons)
        lines = ("WEAPONS / TOOLS",)
        if weapons:
            lines += tuple(
                f"{index + 1}. {weapon.weapon_id} "
                f"{weapon.loaded}/{weapon.reserve}"
                f" {'ACTIVE' if weapon.selected else ''}"
                for index, weapon in enumerate(weapons)
            )
        else:
            lines += ("FIREARMS none",)
        if player.tool is None:
            lines += ("TOOL none",)
        else:
            tool = player.tool
            active = snapshot.mode_status.active_equipment == tool.weapon_id
            lines += (
                f"TOOL Q: {tool.weapon_id} "
                f"{'ACTIVE' if active else 'ready'}",
            )
        return lines

    def draw(self, surface, snapshot):
        lines = self.lines(snapshot)
        font = pygame.font.Font(None, 23)
        line_height = 20
        width = max(font.size(line)[0] for line in lines) + INSET * 2
        height = len(lines) * line_height + INSET * 2
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill(BACKGROUND)
        pygame.draw.rect(panel, BORDER, panel.get_rect(), 2)
        for index, line in enumerate(lines):
            colour = TEXT if index == 0 else MUTED
            panel.blit(
                font.render(line, True, colour), (INSET, INSET + index * line_height)
            )
        surface.blit(
            panel,
            (surface.get_width() - width - 12, surface.get_height() - height - 12),
        )
