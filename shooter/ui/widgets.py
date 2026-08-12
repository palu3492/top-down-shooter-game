"""The widgets the menus are built from.

Thin by design: `pygame_gui` already draws all of these. What this adds is one
place where the object ids live, so a theme change is a theme change and not a
sweep through every screen.
"""

from pygame_gui.elements import (
    UIButton,
    UICheckBox,
    UIDropDownMenu,
    UIHorizontalSlider,
    UILabel,
    UIPanel,
    UISelectionList,
)


def title(rect, text, manager, container=None):
    return UILabel(rect, text, manager, container=container, object_id="#screen_title")


def hint(rect, text, manager, container=None):
    return UILabel(rect, text, manager, container=container, object_id="#screen_hint")


def caption(rect, text, manager, container=None):
    return UILabel(rect, text, manager, container=container, object_id="#caption")


def button(rect, text, manager, container=None):
    return UIButton(rect, text, manager, container=container)


def checkbox(rect, text, manager, container=None, checked=False):
    """`initial_state` rather than `set_state`, which announces the change --
    right for a click, wrong for a screen that is still being built."""
    return UICheckBox(rect, text, manager, container=container, initial_state=checked)


def dropdown(rect, options, manager, container=None, selected=None):
    listed = list(options)
    if not listed:
        raise ValueError("a dropdown needs at least one option")
    return UIDropDownMenu(
        listed,
        listed[0] if selected is None else selected,
        rect,
        manager,
        container=container,
    )


def slider(rect, manager, value, value_range, container=None, increment=1):
    return UIHorizontalSlider(
        rect,
        value,
        value_range,
        manager,
        container=container,
        click_increment=increment,
    )


def selector(rect, options, manager, container=None):
    return UISelectionList(rect, list(options), manager, container=container)


def panel(rect, manager, container=None):
    return UIPanel(rect, manager=manager, container=container)
