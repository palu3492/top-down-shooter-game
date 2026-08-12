"""Placing a rectangle against an edge of the window.

Scaling is not layout. A HUD piece should keep its size and stay the same
distance from the corner it belongs to, whatever the window is -- which is what
`pygame_gui` anchors do for widgets, and what these do for anything drawn with a
plain blit.

The inset is measured *inward from the anchored edge*, never from the origin.
That is the whole difference: `window[0] - 263` only works at one resolution and
only because the art happens to be 223 wide, while "40 in from the right" is
true at every resolution and says what was meant.
"""

import pygame

LEFT, CENTRE, RIGHT = "left", "centre", "right"
TOP, MIDDLE, BOTTOM = "top", "middle", "bottom"

HORIZONTAL = (LEFT, CENTRE, RIGHT)
VERTICAL = (TOP, MIDDLE, BOTTOM)


class UnknownEdgeError(ValueError):
    """An anchor naming an edge that does not exist."""


def _along(length, available, edge, inset, near, far):
    if edge == near:
        return inset
    if edge == far:
        return available - length - inset
    return (available - length) / 2 + inset


def place(size, window, horizontal=LEFT, vertical=TOP, inset=(0, 0)):
    """The rectangle `size` would occupy, anchored to the named edges."""
    if horizontal not in HORIZONTAL:
        raise UnknownEdgeError(f"{horizontal!r} is not one of {HORIZONTAL}")
    if vertical not in VERTICAL:
        raise UnknownEdgeError(f"{vertical!r} is not one of {VERTICAL}")

    width, height = size
    return pygame.Rect(
        _along(width, window[0], horizontal, inset[0], LEFT, RIGHT),
        _along(height, window[1], vertical, inset[1], TOP, BOTTOM),
        width,
        height,
    )


def inside(panel, offset):
    """A position measured from a panel's own corner, so readouts ride with it."""
    return (panel.left + offset[0], panel.top + offset[1])
