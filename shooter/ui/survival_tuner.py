"""Small developer overlay for editing the next Survival run's balance."""

from dataclasses import replace

import pygame

from shooter.survival_balance import save_survival_balance


FIELDS = (
    ("walker_speed", 20),
    ("runner_speed", 20),
    ("breaker_speed", 20),
    ("starting_magazine", 5),
    ("starting_reserve", 5),
    ("kill_reward", 10),
    ("health_regeneration_per_second", 0.25),
    ("preparation_seconds", 5),
)


class SurvivalTuner:
    def __init__(self, balance):
        self.balance = balance
        self.selected = 0
        self.notice = "Changes apply on the next match."

    def handle(self, event):
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(FIELDS)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(FIELDS)
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            name, increment = FIELDS[self.selected]
            direction = -1 if event.key == pygame.K_LEFT else 1
            value = getattr(self.balance, name) + direction * increment
            self.balance = replace(self.balance, **{name: max(0, value)})
            self.notice = "Unsaved changes; S saves for the next match."
        elif event.key == pygame.K_s:
            save_survival_balance(self.balance)
            self.notice = "Saved. Start a fresh match to apply it."

    def draw(self, surface):
        font = pygame.font.Font(None, 24)
        rows = ["SURVIVAL TUNER  TAB close | arrows adjust | S save | 1 pistol | 2 SMG"]
        rows += tuple(
            f"{'>' if index == self.selected else ' '} {name}: "
            f"{getattr(self.balance, name):g}"
            for index, (name, _increment) in enumerate(FIELDS)
        )
        rows.append(self.notice)
        width = max(font.size(row)[0] for row in rows) + 20
        panel = pygame.Surface((width, 24 * len(rows) + 16), pygame.SRCALPHA)
        panel.fill((8, 12, 16, 230))
        pygame.draw.rect(panel, (255, 180, 65), panel.get_rect(), 2)
        for index, row in enumerate(rows):
            panel.blit(font.render(row, True, (235, 235, 235)), (10, 8 + index * 24))
        surface.blit(panel, (12, surface.get_height() - panel.get_height() - 12))
