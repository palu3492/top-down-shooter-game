"""Text-only gameplay diagnostics drawn from immutable values."""

import pygame

PANEL = (12, 12, 520, 214)
BACKGROUND = (8, 12, 16, 205)
BORDER = (75, 170, 190)
TEXT = (225, 235, 238)
MUTED = (155, 175, 180)
LINE_HEIGHT = 20
INSET = 10


class DebugOverlay:
    def lines(self, snapshot, presentation):
        player = next(
            (entity for entity in snapshot.entities if "player" in entity.tags), None
        )
        mode = snapshot.mode_status
        weapon = None
        if player is not None:
            weapon = next((item for item in player.weapons if item.selected), None)

        match_line = (
            f"MATCH {snapshot.mode_id} | MAP {snapshot.map_id} | "
            f"SEED {snapshot.seed} | TICK {snapshot.tick} | {snapshot.state.upper()}"
        )
        mode_line = self._mode_line(mode, snapshot.result)
        player_line = self._player_line(player)
        weapon_line = self._weapon_line(weapon)
        equipment_line = (
            f"EQUIPMENT grenade={presentation.grenades} "
            f"stun={presentation.stun_grenades} "
            f"instakill={presentation.instakill_remaining:.1f}s"
        )
        cargo = ", ".join(f"{item}x{count}" for item, count in presentation.cargo)
        context = presentation.notice or presentation.interaction or "-"
        context_line = f"CARGO {cargo or '-'} | STATUS {context}"
        lines = (
            match_line,
            mode_line,
            player_line,
            weapon_line,
            equipment_line,
            context_line,
        )
        if presentation.shopping:
            offers = " | ".join(
                f"{offer.slot}:{offer.name} ${offer.price}"
                f"{' OWNED' if offer.owned else ''}"
                f"{' TOO-POOR' if not offer.affordable else ''}"
                for offer in presentation.shop_offers
            )
            lines += (f"SHOP {offers or '-'}",)
            if presentation.shop_feedback:
                lines += (f"SHOP STATUS {presentation.shop_feedback}",)
        return lines

    def draw(self, surface, snapshot, presentation):
        lines = self.lines(snapshot, presentation)
        height = max(PANEL[3], INSET * 2 + len(lines) * LINE_HEIGHT)
        panel = pygame.Surface((PANEL[2], height), pygame.SRCALPHA)
        panel.fill(BACKGROUND)
        pygame.draw.rect(panel, BORDER, panel.get_rect(), 2)
        font = pygame.font.Font(None, 23)
        for index, line in enumerate(lines):
            colour = TEXT if index < 5 else MUTED
            panel.blit(
                font.render(line, True, colour),
                (INSET, INSET + index * LINE_HEIGHT),
            )
        surface.blit(panel, PANEL[:2])

    @staticmethod
    def _mode_line(mode, result):
        if mode is None:
            return f"MODE - | RESULT {result or '-'}"
        if hasattr(mode, "wave"):
            target = "∞" if mode.wave_target is None else str(mode.wave_target)
            composition = ",".join(
                f"{kind}:{count}" for kind, count in mode.enemy_composition
            ) or "-"
            return (
                f"MODE {mode.phase} | WAVE {mode.wave}/{target} | "
                f"NEXT {mode.preparation_remaining:.1f}s | "
                f"ENEMIES {mode.enemies_remaining} "
                f"| TYPES {composition} | CASH {mode.cash} "
                f"| RESULT {result or mode.outcome or '-'}"
            )
        title = getattr(mode, "title", type(mode).__name__)
        details = []
        if hasattr(mode, "elapsed"):
            details.append(f"ELAPSED {mode.elapsed:.1f}s")
        if hasattr(mode, "advances"):
            details.append(f"STEPS {mode.advances}")
        if hasattr(mode, "actors_alive"):
            details.append(f"ACTORS {mode.actors_alive}")
        outcome = result or getattr(mode, "outcome", None) or "-"
        detail_text = " | ".join(details)
        return f"MODE {title} | {detail_text} | RESULT {outcome}"

    @staticmethod
    def _player_line(player):
        if player is None:
            return "PLAYER -"
        vital = player.vitality
        health = "-" if vital is None else f"{vital.health:.0f}/{vital.max_health:.0f}"
        armor = "-" if vital is None else f"{vital.armor:.0f}/{vital.max_armor:.0f}"
        position = "-" if player.position is None else (
            f"{player.position[0]:.0f},{player.position[1]:.0f}"
        )
        return (
            f"PLAYER id={player.entity_id} faction={player.faction or '-'} "
            f"pos={position} hp={health} armor={armor}"
        )

    @staticmethod
    def _weapon_line(weapon):
        if weapon is None:
            return "WEAPON -"
        return (
            f"WEAPON {weapon.weapon_id} ammo={weapon.loaded}/{weapon.reserve} "
            f"status={weapon.status or 'ready'} "
            f"cooldown={weapon.cooldown_remaining:.2f}s "
            f"reload={weapon.reload_remaining:.2f}s"
        )
