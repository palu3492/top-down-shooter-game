"""Reading assets, once each.

`functools.cache` keys on the call as it was written, not on the arguments the
function ends up with -- so `load_image(path)` and `load_image(path, False)`
were two entries, two reads of the same file and two copies of the same surface.
Every loader here normalises its arguments before the cache sees them, so the
same file asked for two ways is the same surface.
"""

from functools import cache

import pygame

from shooter.asset_paths import ASSETS_DIR as ASSETS_DIR
from shooter.asset_paths import asset_path


def _cache_controls(public, cached):
    """Keep `cache_info` and `cache_clear` reachable through the public name."""
    public.cache_info = cached.cache_info
    public.cache_clear = cached.cache_clear
    return public


@cache
def _image(relative, alpha):
    image = pygame.image.load(asset_path(relative))
    return image.convert_alpha() if alpha else image


def load_image(relative, alpha=False):
    return _image(relative, bool(alpha))


@cache
def _scaled(relative, factor, alpha):
    image = _image(relative, alpha)
    size = (int(image.get_width() * factor), int(image.get_height() * factor))
    return pygame.transform.scale(image, size)


def load_scaled(relative, factor, alpha=False):
    return _scaled(relative, factor, bool(alpha))


@cache
def _sized(relative, width, height, alpha):
    return pygame.transform.scale(_image(relative, alpha), (width, height))


def load_sized(relative, width, height, alpha=False):
    return _sized(relative, width, height, bool(alpha))


@cache
def _sheet(relative):
    return pygame.image.load(asset_path(relative)).convert()


def load_sheet(relative):
    """A large image sampled from rather than blitted whole.

    Cached like everything else: a world background is expensive to read and
    convert, which should be paid once for the process rather than once per game.
    """
    return _sheet(relative)


@cache
def _sound(relative):
    return pygame.mixer.Sound(asset_path(relative))


def load_sound(relative):
    return _sound(relative)


@cache
def _animation(directory, prefix, count, factor, alpha):
    return tuple(
        load_scaled(f"{directory}/{prefix}{i}.png", factor, alpha) for i in range(count)
    )


def load_animation(directory, prefix, count, factor, alpha=False):
    return _animation(directory, prefix, count, factor, bool(alpha))


for _public, _cached in (
    (load_image, _image),
    (load_scaled, _scaled),
    (load_sized, _sized),
    (load_sheet, _sheet),
    (load_sound, _sound),
    (load_animation, _animation),
):
    _cache_controls(_public, _cached)
