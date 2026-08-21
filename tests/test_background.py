from types import SimpleNamespace

import pygame

from shooter.background import TiledBackground


class ImageLayer:
    def __init__(self, image, offsetx=0, offsety=0):
        self.image = image
        self.offsetx = offsetx
        self.offsety = offsety


class ImageObject:
    def __init__(self, image, x, y, height):
        self.image = image
        self.x = x
        self.y = y
        self.height = height


class ObjectLayer(list):
    def __init__(self, objects, offsetx=0, offsety=0):
        super().__init__(objects)
        self.offsetx = offsetx
        self.offsety = offsety


class RecordingScreen:
    def __init__(self):
        self.blits = []

    def blit(self, image, at):
        self.blits.append((image, at))


def background(monkeypatch):
    image = pygame.Surface((100, 80))
    tiled_map = SimpleNamespace(
        visible_layers=[ImageLayer(image, 12, 18)],
        width=10,
        height=8,
        tilewidth=10,
        tileheight=10,
    )
    monkeypatch.setattr("shooter.background.TiledImageLayer", ImageLayer)
    monkeypatch.setattr("shooter.background.load_tiled_map", lambda _: tiled_map)
    return TiledBackground("Maps/test/gas_station.tmx"), image


def test_draws_the_background_authored_in_tiled(monkeypatch):
    ground, _image = background(monkeypatch)
    screen = RecordingScreen()

    ground.draw(screen, 0, 0)

    assert screen.blits[0][0].get_size() == (100, 80)
    assert screen.blits[0][1] == (12, 18)


def test_tiled_background_uses_the_camera_offset(monkeypatch):
    ground, _ = background(monkeypatch)
    screen = RecordingScreen()

    ground.draw(screen, -400, -250)

    assert screen.blits[0][1] == (-388, -232)


def test_world_size_comes_from_the_tiled_map(monkeypatch):
    ground, _ = background(monkeypatch)

    assert ground.size == (100, 80)


def test_draws_visible_tiled_image_objects_at_authored_position(monkeypatch):
    backdrop = pygame.Surface((100, 80))
    vehicle = pygame.Surface((24, 15))
    object_layer = ObjectLayer([ImageObject(vehicle, 30, 25, 15)], 4, 6)
    tiled_map = SimpleNamespace(
        visible_layers=[ImageLayer(backdrop), object_layer],
        width=10,
        height=8,
        tilewidth=10,
        tileheight=10,
    )
    monkeypatch.setattr("shooter.background.TiledImageLayer", ImageLayer)
    monkeypatch.setattr("shooter.background.TiledObjectGroup", ObjectLayer)
    monkeypatch.setattr("shooter.background.load_tiled_map", lambda _: tiled_map)
    ground = TiledBackground("Maps/world_1/world_1.tmx")
    screen = RecordingScreen()

    ground.draw(screen, -10, -20)

    assert screen.blits[1] == (vehicle, (24, 26))
