from functools import cache

import pygame
from pytmx import TiledImageLayer, TiledObjectGroup
from pytmx.util_pygame import load_pygame

from shooter.assets import asset_path

@cache
def load_tiled_map(relative):
    return load_pygame(asset_path(relative))


class TiledBackground:
    """Draw the visible image layers authored in Tiled."""

    def __init__(self, relative):
        self.map = load_tiled_map(relative)
        self.size = (
            self.map.width * self.map.tilewidth,
            self.map.height * self.map.tileheight,
        )
        self.images = {
            id(layer): layer.image
            for layer in self.map.visible_layers
            if isinstance(layer, TiledImageLayer)
        }
        self.object_images = {
            id(obj): self._scaled_object_image(obj)
            for layer in self.map.visible_layers
            if isinstance(layer, TiledObjectGroup)
            for obj in layer
            if obj.image is not None
        }

    def draw(self, screen, camera_x, camera_y):
        for layer in self.map.visible_layers:
            if isinstance(layer, TiledImageLayer):
                screen.blit(
                    self.images[id(layer)],
                    (
                        camera_x + getattr(layer, "offsetx", 0),
                        camera_y + getattr(layer, "offsety", 0),
                    ),
                )
            elif isinstance(layer, TiledObjectGroup):
                offset_x = getattr(layer, "offsetx", 0)
                offset_y = getattr(layer, "offsety", 0)
                for obj in layer:
                    if obj.image is None:
                        continue
                    # PyTMX normalizes tile objects to a bottom-left origin by
                    # subtracting their height. This map's image-collection
                    # tileset is explicitly top-left aligned, so restore the
                    # authored Tiled position when drawing its image objects.
                    screen.blit(
                        self.object_images[id(obj)],
                        (
                            camera_x + offset_x + obj.x,
                            camera_y + offset_y + obj.y + obj.height,
                    ),
                )

    @staticmethod
    def _scaled_object_image(obj):
        width = round(getattr(obj, "width", obj.image.get_width()))
        height = round(getattr(obj, "height", obj.image.get_height()))
        size = (max(1, width), max(1, height))
        return (
            obj.image
            if obj.image.get_size() == size
            else pygame.transform.smoothscale(obj.image, size)
        )
