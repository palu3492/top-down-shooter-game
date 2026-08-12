"""The layout grid.

Pure arithmetic with no display behind it, so the interesting cases can be
enumerated rather than sampled. Off-by-one errors in a layout are invisible
until someone squints at a screenshot; here they are a failing assertion.
"""

import itertools
from itertools import pairwise

import pygame
import pytest

from shooter.ui.layout import Grid, LayoutOverflowError, Row

AREA = pygame.Rect(40, 40, 1000, 640)


def partitions(total):
    """Every way to cut `total` columns into consecutive spans."""
    for cuts in range(total):
        for combination in itertools.combinations(range(1, total), cuts):
            edges = (0, *combination, total)
            yield tuple(b - a for a, b in pairwise(edges))


@pytest.mark.parametrize("columns", range(1, 13))
def test_a_full_span_fills_the_row_exactly(columns):
    row = Row(AREA, columns=columns)
    assert row.cell(columns) == AREA


@pytest.mark.parametrize("columns", [1, 2, 3, 4, 6, 12])
def test_every_partition_starts_left_and_ends_right(columns):
    for spans in partitions(columns):
        row = Row(AREA, columns=columns)
        cells = [row.cell(span) for span in spans]
        assert cells[0].left == AREA.left, spans
        assert cells[-1].right == AREA.right, spans


@pytest.mark.parametrize("columns", [1, 2, 3, 4, 6, 12])
def test_neighbours_are_separated_by_exactly_one_gutter(columns):
    for spans in partitions(columns):
        row = Row(AREA, columns=columns, gutter=12)
        cells = [row.cell(span) for span in spans]
        gaps = [b.left - a.right for a, b in pairwise(cells)]
        assert all(gap == 12 for gap in gaps), (spans, gaps)


@pytest.mark.parametrize("columns", [1, 2, 3, 5, 7, 12])
def test_cells_tile_the_row_when_there_is_no_gutter(columns):
    row = Row(AREA, columns=columns, gutter=0)
    cells = [row.cell(1) for _ in range(columns)]
    assert sum(cell.width for cell in cells) == AREA.width
    assert all(b.left == a.right for a, b in pairwise(cells))


@pytest.mark.parametrize("columns", range(1, 13))
def test_equal_spans_never_differ_by_more_than_a_pixel(columns):
    """Rounding has to land somewhere; it must not pile up on one cell."""
    row = Row(AREA, columns=columns)
    widths = [row.cell(1).width for _ in range(columns)]
    assert max(widths) - min(widths) <= 1


def test_a_cell_keeps_the_full_height_of_its_row():
    row = Row(AREA, columns=4)
    cell = row.cell(1)
    assert (cell.top, cell.height) == (AREA.top, AREA.height)


def test_an_inset_shrinks_a_cell_on_every_side():
    plain = Row(AREA, columns=4).cell(2)
    inset = Row(AREA, columns=4).cell(2, inset=5)
    assert inset.width == plain.width - 10
    assert inset.height == plain.height - 10
    assert inset.center == plain.center


def test_a_row_cannot_hand_out_more_than_it_has():
    row = Row(AREA, columns=12)
    row.cell(8)
    assert row.free_columns == 4
    with pytest.raises(LayoutOverflowError):
        row.cell(5)


def test_a_cell_spans_at_least_one_column():
    with pytest.raises(LayoutOverflowError):
        Row(AREA, columns=12).cell(0)


def test_skipping_leaves_a_hole_the_size_of_the_skip():
    row = Row(AREA, columns=12)
    first = row.cell(3)
    row.skip(3)
    after = row.cell(3)
    assert after.left - first.right > 3 * (AREA.width / 12)


def test_skipping_past_the_end_is_refused():
    row = Row(AREA, columns=12)
    row.skip(10)
    with pytest.raises(LayoutOverflowError):
        row.skip(3)


def test_rest_claims_everything_left():
    row = Row(AREA, columns=12)
    row.cell(5)
    assert row.rest().right == AREA.right
    assert row.free_columns == 0


def test_rows_stack_downwards_separated_by_the_gutter():
    grid = Grid(AREA, gutter=10)
    first = grid.row(40).rest()
    second = grid.row(40).rest()
    assert first.top == AREA.top
    assert second.top - first.bottom == 10


def test_a_grid_reports_the_height_it_has_left():
    grid = Grid(AREA, gutter=10)
    assert grid.free_height == AREA.height
    grid.row(100)
    assert grid.free_height == AREA.height - 110


def test_a_row_taller_than_the_grid_is_refused():
    grid = Grid(AREA)
    with pytest.raises(LayoutOverflowError):
        grid.row(AREA.height + 1)


def test_a_row_is_at_least_a_pixel_tall():
    with pytest.raises(LayoutOverflowError):
        Grid(AREA).row(0)


def test_the_last_row_reaches_the_bottom():
    grid = Grid(AREA)
    grid.row(100)
    assert grid.rest().rest().bottom == AREA.bottom


def test_padding_insets_the_whole_grid():
    grid = Grid(AREA, padding=20)
    assert grid.rest().rest() == AREA.inflate(-40, -40)


def test_a_grid_built_on_a_cell_stays_inside_it():
    outer = Grid(AREA).row(300)
    cell = outer.cell(7)
    inner = Grid(cell, columns=3, padding=6).rest()
    nested = [inner.cell(1) for _ in range(3)]
    assert all(cell.contains(rect) for rect in nested)


def test_a_grid_refuses_to_hand_out_its_remainder_twice():
    grid = Grid(AREA)
    grid.rest()
    with pytest.raises(LayoutOverflowError):
        grid.rest()


def test_a_grid_does_not_move_the_rect_it_was_given():
    area = pygame.Rect(AREA)
    Grid(area, padding=25).row(50)
    assert area == AREA
