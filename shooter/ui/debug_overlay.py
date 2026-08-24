"""Text-only gameplay diagnostics drawn from immutable values."""

import pygame

PANEL = (12, 12, 520, 0)
BACKGROUND = (8, 12, 16, 205)
BORDER = (75, 170, 190)
TEXT = (225, 235, 238)
MUTED = (155, 175, 180)
LINE_HEIGHT = 17
INSET = 10


class DebugOverlay:
    def lines(self, snapshot, presentation):
        player = next(
            (entity for entity in snapshot.entities if "player" in entity.tags), None
        )
        mode = snapshot.mode_status
        match_line = (
            f"MATCH {snapshot.mode_id} | MAP {snapshot.map_id} | "
            f"SEED {snapshot.seed} | TICK {snapshot.tick} | {snapshot.state.upper()}"
        )
        mode_line = self._mode_line(mode, snapshot.result)
        player_line = self._player_line(player)
        equipment_line = (
            f"EQUIPMENT grenade={presentation.grenades} "
            f"stun={presentation.stun_grenades} "
            f"instakill={presentation.instakill_remaining:.1f}s"
        )
        cargo = ", ".join(f"{item}x{count}" for item, count in presentation.cargo)
        interaction = getattr(mode, "interaction_context", None)
        interaction_result = getattr(mode, "interaction_result", None)
        purchase_result = getattr(mode, "purchase_result", None)
        station_result = getattr(mode, "station_result", None)
        consumable_purchase_result = getattr(mode, "consumable_purchase_result", None)
        health_pack_result = getattr(mode, "health_pack_result", None)
        harvest_result = getattr(mode, "harvest_result", None)
        harvest_context = getattr(mode, "harvest_context", None)
        construction_result = getattr(mode, "construction_result", None)
        neutral_context = None if interaction is None else interaction.prompt
        if neutral_context is None and harvest_context is not None:
            neutral_context = harvest_context.prompt
        if interaction_result is not None:
            neutral_context = (
                f"INTERACT {interaction_result.reason} "
                f"{interaction_result.interaction_id or '-'}"
            )
        if purchase_result is not None:
            neutral_context = (
                f"PURCHASE {purchase_result.reason} "
                f"{purchase_result.weapon_id or '-'} "
                f"balance={purchase_result.balance}"
            )
        if station_result is not None:
            neutral_context = (
                f"STATION {station_result.kind} {station_result.reason} "
                f"amount={station_result.amount:g} "
                f"balance={station_result.balance}"
            )
        if consumable_purchase_result is not None:
            neutral_context = (
                f"CONSUMABLE {consumable_purchase_result.reason} "
                f"{consumable_purchase_result.item_id or '-'}x"
                f"{consumable_purchase_result.amount} "
                f"balance={consumable_purchase_result.balance}"
            )
        if health_pack_result is not None:
            neutral_context = (
                f"HEALTH PACK {health_pack_result.reason} "
                f"restored={health_pack_result.restored:g} "
                f"remaining={health_pack_result.remaining}"
            )
        if harvest_result is not None:
            neutral_context = (
                f"HARVEST {harvest_result.reason} "
                f"{harvest_result.harvestable_id or '-'} "
                f"durability={harvest_result.remaining_durability} "
                f"yield={harvest_result.resource_id or '-'}x"
                f"{harvest_result.resource_amount}"
            )
        if construction_result is not None:
            neutral_context = (
                f"BARRICADE {construction_result.reason} "
                f"{construction_result.anchor_id} "
                f"hp={construction_result.health}/{construction_result.max_health}"
            )
        context = (
            presentation.notice
            or presentation.interaction
            or neutral_context
            or "-"
        )
        context_line = f"CARGO {cargo or '-'} | STATUS {context}"
        lines = (
            match_line,
            mode_line,
            player_line,
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
        font = pygame.font.Font(None, 19)
        available_width = max(1, surface.get_width() // 3 - PANEL[0] * 2)
        content_width = max((font.size(line)[0] for line in lines), default=0)
        width = min(available_width, max(1, min(PANEL[2], content_width + INSET * 2)))
        height = max(PANEL[3], INSET * 2 + len(lines) * LINE_HEIGHT)
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill(BACKGROUND)
        pygame.draw.rect(panel, BORDER, panel.get_rect(), 2)
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
            resources = ",".join(
                f"{kind}:{count}" for kind, count in mode.resources
            ) or "-"
            consumables = ",".join(
                f"{kind}:{count}" for kind, count in mode.consumables
            ) or "-"
            return (
                f"MODE {mode.phase} | WAVE {mode.wave}/{target} | "
                f"NEXT {mode.preparation_remaining:.1f}s | "
                f"ENEMIES {mode.enemies_remaining} "
                f"| PENDING {mode.pending_enemies} "
                f"| TYPES {composition} | CASH {mode.cash} "
                f"| RESOURCES {resources} "
                f"| CONSUMABLES {consumables} "
                f"| ACTIVE {mode.active_equipment or '-'} "
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
            f"range={weapon.effective_range or '-'}-{weapon.max_range or '-'} "
            f"spread={weapon.spread:g} "
            f"cooldown={weapon.cooldown_remaining:.2f}s "
            f"reload={weapon.reload_remaining:.2f}s"
        )

    @staticmethod
    def _loadout_line(player):
        if player is None or not player.weapons:
            return "LOADOUT -"
        slots = " | ".join(
            f"{index + 1}:{weapon.weapon_id}"
            f" {weapon.loaded}/{weapon.reserve}"
            f"{' *' if weapon.selected else ''}"
            for index, weapon in enumerate(player.weapons)
        )
        return f"LOADOUT {slots}"

    @staticmethod
    def _tool_line(player):
        if player is None or player.tool is None:
            return "TOOL -"
        tool = player.tool
        return (
            f"TOOL Q:{tool.weapon_id} status={tool.status or 'ready'} "
            f"cooldown={tool.cooldown_remaining:.2f}s"
        )
