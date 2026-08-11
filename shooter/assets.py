from functools import lru_cache
from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).resolve().parent.parent / "Assets"


def asset_path(relative):
    return str(ASSETS_DIR / relative)


@lru_cache(maxsize=None)
def load_image(relative, alpha=False):
    image = pygame.image.load(asset_path(relative))
    return image.convert_alpha() if alpha else image


@lru_cache(maxsize=None)
def load_scaled(relative, factor, alpha=False):
    image = load_image(relative, alpha)
    size = (int(image.get_width() * factor), int(image.get_height() * factor))
    return pygame.transform.scale(image, size)


@lru_cache(maxsize=None)
def load_sized(relative, width, height, alpha=False):
    return pygame.transform.scale(load_image(relative, alpha), (width, height))


@lru_cache(maxsize=None)
def load_sound(relative):
    return pygame.mixer.Sound(asset_path(relative))


@lru_cache(maxsize=None)
def load_animation(directory, prefix, count, factor, alpha=False):
    return tuple(
        load_scaled(f"{directory}/{prefix}{i}.png", factor, alpha) for i in range(count)
    )
