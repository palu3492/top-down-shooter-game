from functools import cache
from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).resolve().parent.parent / "Assets"


def asset_path(relative):
    return str(ASSETS_DIR / relative)


@cache
def load_image(relative, alpha=False):
    image = pygame.image.load(asset_path(relative))
    return image.convert_alpha() if alpha else image


@cache
def load_scaled(relative, factor, alpha=False):
    image = load_image(relative, alpha)
    size = (int(image.get_width() * factor), int(image.get_height() * factor))
    return pygame.transform.scale(image, size)


@cache
def load_sized(relative, width, height, alpha=False):
    return pygame.transform.scale(load_image(relative, alpha), (width, height))


@cache
def load_sound(relative):
    return pygame.mixer.Sound(asset_path(relative))


@cache
def load_animation(directory, prefix, count, factor, alpha=False):
    return tuple(
        load_scaled(f"{directory}/{prefix}{i}.png", factor, alpha) for i in range(count)
    )
