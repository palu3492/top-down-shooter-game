"""Turning settings into controls.

A setting already declares everything needed to pick its control: a switch is a
checkbox, a fixed set of options is a dropdown, a bounded number is a slider.
So a form is not a thing to configure, it is a thing to derive.

Every control takes its starting value in its constructor rather than through a
setter afterwards. `UICheckBox.set_state` announces the change, and a form
populating itself is not the player editing it.
"""

import copy

import pygame
import pygame_gui

from shooter.settings import BOOT, Settings
from shooter.ui import widgets
from shooter.ui.screens import Screen

LABEL_SPAN = 5
CONTROL_SPAN = 5
READOUT_SPAN = 2

ROW_HEIGHT = 34
# A section header already says "new spawns"; only the restart warning has to
# ride along with the row, because nothing else on that screen says it.
NOTE = {BOOT: "restart"}


def resolution_text(size):
    return f"{size[0]} x {size[1]}"


class Field:
    """One setting, as a caption and whatever control its type implies."""

    def __init__(self, setting, value, row, manager, add):
        self.setting = setting
        self.start = value
        add(widgets.caption(row.cell(LABEL_SPAN), self.label, manager))
        self.control = self._build(row.cell(CONTROL_SPAN), value, manager)
        add(self.control)
        self.readout = add(widgets.caption(row.cell(READOUT_SPAN), "", manager))
        self._show_value()

    @property
    def label(self):
        return self.setting.name.replace("_", " ").lower()

    @property
    def changed(self):
        return self.value != self.start

    def _build(self, rect, value, manager):
        setting = self.setting
        if isinstance(setting.default, bool):
            return widgets.checkbox(rect, "", manager, checked=value)
        if setting.choices is not None:
            return widgets.dropdown(
                rect,
                [self._option_text(choice) for choice in setting.choices],
                manager,
                selected=self._option_text(value),
            )
        return widgets.slider(
            rect,
            manager,
            value,
            (setting.minimum, setting.maximum),
            increment=self._increment,
        )

    @property
    def _increment(self):
        return 0.1 if isinstance(self.setting.default, float) else 1

    def _option_text(self, choice):
        return resolution_text(choice) if isinstance(choice, tuple) else str(choice)

    @property
    def value(self):
        setting = self.setting
        if isinstance(setting.default, bool):
            return self.control.get_state()
        if setting.choices is not None:
            chosen = self.control.selected_option[0]
            for choice in setting.choices:
                if self._option_text(choice) == chosen:
                    return choice
            return self.start
        return type(setting.default)(self.control.get_current_value())

    def handle(self, event):
        """True when this field's own control moved."""
        if getattr(event, "ui_element", None) is not self.control:
            return False
        self._show_value()
        return True

    def _show_value(self):
        note = NOTE.get(self.setting.applies, "")
        if isinstance(self.setting.default, bool) or self.setting.choices is not None:
            self.readout.set_text(note)
            return
        shown = (
            f"{self.value:g}" if isinstance(self.setting.default, float) else self.value
        )
        self.readout.set_text(f"{shown}  {note}".strip())


class Form:
    """The fields on a screen, and the draft they are editing."""

    CHANGE_EVENTS = (
        pygame_gui.UI_CHECK_BOX_CHECKED,
        pygame_gui.UI_CHECK_BOX_UNCHECKED,
        pygame_gui.UI_DROP_DOWN_MENU_CHANGED,
        pygame_gui.UI_HORIZONTAL_SLIDER_MOVED,
    )

    def __init__(self, draft, manager, add):
        self.draft = draft
        self.manager = manager
        self.add = add
        self.fields = []

    def build(self, grid, names):
        for name in names:
            setting = self.draft.setting(name)
            self.fields.append(
                Field(
                    setting,
                    self.draft[name],
                    grid.row(ROW_HEIGHT),
                    self.manager,
                    self.add,
                )
            )
        return self

    @property
    def changed(self):
        return any(field.changed for field in self.fields)

    def handle(self, event):
        if event.type not in self.CHANGE_EVENTS:
            return False
        return any(field.handle(event) for field in self.fields)

    def commit(self):
        """Write the controls into the draft. Nothing before this touches it."""
        for field in self.fields:
            self.draft.set(field.setting.name, field.value)


def height_for(names, per_row=ROW_HEIGHT, gutter=12):
    return len(names) * (per_row + gutter)


class FormScreen(Screen):
    """A screen whose edits live in a draft until Save.

    The real store is untouched while the player is still dragging, so leaving
    discards and Save has somewhere sensible to raise the restart warning.
    """

    SAVED = "settings saved"
    UNSAVED = "nothing is saved until you press save"

    def __init__(self, window, manager, settings=None):
        super().__init__(window, manager)
        self.settings = settings if settings is not None else Settings()
        self.draft = copy.deepcopy(self.settings)
        self.confirming = None
        self.form = Form(self.draft, self.manager, self.add)

    def build_form(self, grid, names, title=None):
        if title is not None:
            self.add(widgets.caption(grid.row(ROW_HEIGHT).rest(), title, self.manager))
        return self.form.build(grid, names)

    def save(self):
        self.form.commit()
        waiting = tuple(
            sorted(
                field.setting.name
                for field in self.form.fields
                if field.changed and field.setting.applies == BOOT
            )
        )
        if waiting:
            self.confirming = confirmation(self.window, self.manager, waiting)
            return
        self.persist()

    def persist(self):
        for name, value in self.draft.values.items():
            self.settings.set(name, value)
        self.settings.save()
        self.settings.apply()
        self.announce(self.SAVED)

    def announce(self, message):
        if getattr(self, "hint", None) is not None:
            self.hint.set_text(message)

    def handle_dialog(self, event):
        """True while a dialog owns the screen and the caller should stand off."""
        if self.confirming is None:
            return False
        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            self.confirming = None
            self.persist()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            self.confirming = None
        return True

    def close(self):
        if self.confirming is not None:
            self.confirming.kill()
            self.confirming = None
        super().close()


def confirmation(window, manager, waiting):
    """Boot-only settings were accepted into the draft but cannot take effect."""
    listed = ", ".join(name.replace("_", " ").lower() for name in waiting)
    rect = pygame.Rect(0, 0, 460, 220)
    rect.center = (window[0] // 2, window[1] // 2)
    return pygame_gui.windows.UIConfirmationDialog(
        rect,
        f"{listed} only changes when the game restarts. Save anyway?",
        manager,
        window_title="RESTART NEEDED",
        action_short_name="SAVE",
        blocking=True,
    )
