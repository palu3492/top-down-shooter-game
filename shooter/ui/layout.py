"""Dividing a rectangle into rows and columns.

`pygame_gui` positions every element with a `relative_rect`, so what the menus
were missing was never a widget -- it was something to compute those rects. A
grid divides an area into rows; a row hands out cells measured in columns.

Nothing here touches a display, a manager or an element. It is arithmetic, and
the results are rectangles.
"""

import pygame

COLUMNS = 12
GUTTER = 12


class LayoutOverflowError(Exception):
    """More was asked of a grid or a row than it has space for."""


class Row:
    """A horizontal band, handed out left to right in column spans."""

    def __init__(self, area, columns=COLUMNS, gutter=GUTTER):
        self.area = area
        self.columns = columns
        self.gutter = gutter
        self.claimed = 0

    @property
    def free_columns(self):
        return self.columns - self.claimed

    def cell(self, span=1, inset=0):
        if span < 1:
            raise LayoutOverflowError(f"a cell spans at least one column, got {span}")
        if span > self.free_columns:
            raise LayoutOverflowError(
                f"{span} columns requested, {self.free_columns} of {self.columns} left"
            )
        left = self._column_start(self.claimed)
        right = self._column_start(self.claimed + span) - self.gutter
        self.claimed += span
        return pygame.Rect(left, self.area.top, right - left, self.area.height).inflate(
            -2 * inset, -2 * inset
        )

    def skip(self, span=1):
        if span > self.free_columns:
            raise LayoutOverflowError(
                f"cannot skip {span} of {self.free_columns} remaining columns"
            )
        self.claimed += span
        return self

    def rest(self, inset=0):
        return self.cell(self.free_columns, inset)

    def _column_start(self, column_index):
        return self.area.left + round(column_index * self._column_pitch)

    @property
    def _column_pitch(self):
        """One column plus the gutter that follows it.

        Measuring every edge from the area's left rather than accumulating
        widths is what keeps the last column flush with the right edge.
        """
        return (self.area.width + self.gutter) / self.columns


class Grid:
    """An area handed out top to bottom in rows of a stated height."""

    def __init__(self, area, columns=COLUMNS, gutter=GUTTER, padding=0):
        self.area = pygame.Rect(area).inflate(-2 * padding, -2 * padding)
        self.columns = columns
        self.gutter = gutter
        self.next_top = self.area.top

    @property
    def free_height(self):
        return self.area.bottom - self.next_top

    def row(self, height, gutter=None):
        if height < 1:
            raise LayoutOverflowError(f"a row is at least one pixel tall, got {height}")
        if height > self.free_height:
            raise LayoutOverflowError(
                f"a {height}px row does not fit in {self.free_height}px of "
                f"remaining grid"
            )
        area = pygame.Rect(self.area.left, self.next_top, self.area.width, height)
        self.next_top += height + (self.gutter if gutter is None else gutter)
        return Row(area, self.columns, self.gutter)

    def skip(self, height):
        self.next_top += height
        return self

    def rest(self):
        return self.row(self.free_height)
