import pygame

from shooter.background import TiledBackground


class RecordingScreen:
    def __init__(self, size):
        self.size = size
        self.blits = []

    def get_width(self):
        return self.size[0]

    def get_height(self):
        return self.size[1]

    def blit(self, image, at):
        self.blits.append((image, at))


def background(monkeypatch, size=(64, 48)):
    tile = pygame.Surface(size)
    monkeypatch.setattr("shooter.background.load_image", lambda _: tile)
    return TiledBackground("tile.png"), tile


def test_tiles_cover_a_window_larger_than_the_texture(monkeypatch):
    ground, tile = background(monkeypatch)
    screen = RecordingScreen((150, 110))

    ground.draw(screen, 0, 0)

    assert [at for image, at in screen.blits if image is tile] == [
        (0, 0),
        (64, 0),
        (128, 0),
        (0, 48),
        (64, 48),
        (128, 48),
        (0, 96),
        (64, 96),
        (128, 96),
    ]


def test_tile_origin_wraps_with_positive_world_coordinates(monkeypatch):
    ground, _ = background(monkeypatch)
    screen = RecordingScreen((100, 80))

    ground.draw(screen, 70, 53)

    assert screen.blits[0][1] == (-6, -5)


def test_tile_origin_wraps_with_negative_world_coordinates(monkeypatch):
    ground, _ = background(monkeypatch)
    screen = RecordingScreen((100, 80))

    ground.draw(screen, -5, -7)

    assert screen.blits[0][1] == (-59, -41)
