"""The size everything is drawn against.

One value rather than a tuple copied into every object that needs it. Most
readers already ask for the size at the moment they use it -- they were only
stale because each held its own copy. Sharing this instead makes them live, and
a resolution change becomes one write.

It behaves as the `(width, height)` pair it replaces, so a plain tuple is still
a valid argument anywhere a viewport is expected.
"""

import pygame


def visible_world(camera, window):
    """The rectangle of the world currently on screen.

    A sprite is drawn at `world + camera`, so the world coordinate sitting at
    the top-left of the display is `-camera`. Anything that needs to reason
    about where the player actually is -- spawning, culling -- wants this rather
    than the window size on its own.
    """
    return pygame.Rect(-camera[0], -camera[1], window[0], window[1])


class Viewport:
    def __init__(self, size):
        self.size = tuple(size)

    def __getitem__(self, index):
        return self.size[index]

    def __len__(self):
        return len(self.size)

    def __iter__(self):
        return iter(self.size)

    def __eq__(self, other):
        return tuple(self.size) == tuple(other)

    def __hash__(self):
        return hash(self.size)

    def __repr__(self):
        return f"Viewport{self.size}"

    @property
    def centre(self):
        return (self.size[0] / 2.0, self.size[1] / 2.0)

    def resize(self, size):
        self.size = tuple(size)
