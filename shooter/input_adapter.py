"""Translate pygame input at the application boundary into neutral commands."""

import pygame

from shooter import commands


class PygameInputAdapter:
    def sample(self, pressed, pointer, window, trigger_held=False):
        move_x = int(bool(pressed[pygame.K_d])) - int(bool(pressed[pygame.K_a]))
        move_y = int(bool(pressed[pygame.K_s])) - int(bool(pressed[pygame.K_w]))
        aim = (
            int(pointer[0] - window[0] / 2),
            -int(pointer[1] - window[1] / 2),
        )
        return commands.ControlFrame((move_x, move_y), aim, bool(trigger_held))

    def action_for(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return commands.ActionCommand(commands.FIRE)
        if event.type != pygame.KEYDOWN:
            return None

        actions = {
            pygame.K_e: commands.INTERACT,
            pygame.K_g: commands.USE_GRENADE,
            pygame.K_f: commands.USE_STUN_GRENADE,
            pygame.K_r: commands.RELOAD,
            pygame.K_SPACE: commands.SKIP_PHASE,
            pygame.K_0: commands.GRANT_ALL,
        }
        if event.key in actions:
            return commands.ActionCommand(actions[event.key])

        slots = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5)
        if event.key in slots:
            return commands.ActionCommand(commands.SELECT_SLOT, slots.index(event.key))
        return None

    def legacy_controls(self, pressed, aim=(0, 0), trigger_held=False):
        """Compatibility for tests/callers that still supply pygame key state."""
        move_x = int(bool(pressed[pygame.K_d])) - int(bool(pressed[pygame.K_a]))
        move_y = int(bool(pressed[pygame.K_s])) - int(bool(pressed[pygame.K_w]))
        return commands.ControlFrame((move_x, move_y), aim, bool(trigger_held))
