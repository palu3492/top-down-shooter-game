"""Readable temporary HUD for playtesting snapshot-owned Survival state."""

import pygame

from shooter.ui.debug_overlay import BACKGROUND, BORDER, INSET, MUTED, TEXT

BOX = (146, 76)
GAP = 10
ACTIVE = (255, 180, 65)


class PlaytestHud:
    def draw(self, surface, snapshot):
        player = next(
            (entity for entity in snapshot.entities if "player" in entity.tags), None
        )
        if player is None:
            return
        self._draw_health_cash(surface, snapshot, player)
        self._draw_resources(surface, snapshot.mode_status.resources)
        self._draw_slots(surface, snapshot, player)

    def _draw_health_cash(self, surface, snapshot, player):
        vital = player.vitality
        health = "-" if vital is None else f"{vital.health:.0f}/{vital.max_health:.0f}"
        self._panel(
            surface,
            (surface.get_width() // 2 - 130, 12, 260, 52),
            (f"HEALTH {health}", f"CASH ${snapshot.mode_status.cash}"),
        )

    def _draw_resources(self, surface, resources):
        values = dict(resources)
        right = surface.get_width() - 12
        for index, resource in enumerate(("wood", "metal")):
            rect = pygame.Rect(right - (index + 1) * 94 - index * 8, 12, 94, 52)
            self._panel(
                surface,
                rect,
                (resource.upper(), str(values.get(resource, 0))),
            )

    def _draw_slots(self, surface, snapshot, player):
        total_width = BOX[0] * 3 + GAP * 2
        left = surface.get_width() // 2 - total_width // 2
        top = surface.get_height() - BOX[1] - 16
        tool = player.tool
        active = snapshot.mode_status.active_equipment
        tool_lines = (
            "Q  TOOL",
            "NONE" if tool is None else tool.weapon_id.replace("survivor_", "").upper(),
        )
        self._slot(
            surface,
            pygame.Rect(left, top, *BOX),
            tool_lines,
            tool is not None and active == tool.weapon_id,
        )
        for index in range(2):
            weapon = player.weapons[index] if index < len(player.weapons) else None
            lines = (f"{index + 1}  FIREARM", "EMPTY")
            is_active = False
            if weapon is not None:
                lines = (
                    f"{index + 1}  FIREARM",
                    weapon.weapon_id.replace("survivor_", "").upper(),
                    f"AMMO {weapon.loaded}/{weapon.reserve}",
                )
                is_active = active == weapon.weapon_id
            self._slot(
                surface,
                pygame.Rect(left + (BOX[0] + GAP) * (index + 1), top, *BOX),
                lines,
                is_active,
            )

    def _slot(self, surface, rect, lines, active):
        colour = ACTIVE if active else BORDER
        pygame.draw.rect(surface, BACKGROUND, rect)
        pygame.draw.rect(surface, colour, rect, 2)
        font = pygame.font.Font(None, 21)
        for index, line in enumerate(lines):
            text = font.render(line, True, TEXT if index else colour)
            surface.blit(text, (rect.left + INSET, rect.top + 8 + index * 20))

    def _panel(self, surface, rect, lines):
        rect = pygame.Rect(rect)
        pygame.draw.rect(surface, BACKGROUND, rect)
        pygame.draw.rect(surface, BORDER, rect, 2)
        font = pygame.font.Font(None, 21)
        for index, line in enumerate(lines):
            text = font.render(line, True, TEXT if index else MUTED)
            surface.blit(text, (rect.left + INSET, rect.top + 5 + index * 22))
