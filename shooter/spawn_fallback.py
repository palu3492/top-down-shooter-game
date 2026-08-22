"""Named renderer-independent placement policies for incomplete map data."""


def visible_ring_position(window, visible, margin, rng):
    if visible is None:
        left, top, width, height = 0, 0, window[0], window[1]
    else:
        left, top = visible.left, visible.top
        width, height = visible.width, visible.height
    right, bottom = left + width, top + height
    side = rng.randint(1, 4)
    if side == 1:
        return (rng.randint(left, right), top - margin)
    if side == 2:
        return (rng.randint(left, right), bottom + margin)
    if side == 3:
        return (left - margin, rng.randint(top, bottom))
    return (right + margin, rng.randint(top, bottom))
