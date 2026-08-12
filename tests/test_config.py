import pygame

from shooter import config
from shooter.entities.player import Human
from shooter.entities.projectiles import Shot
from shooter.entities.zombie import Zombie
from shooter.systems.waves import WaveSystem
from shooter.ui.hud import GunData
from shooter.ui.radar import RadarScreen


def blip_at(surface, colour):
    left, top = config.RADAR_ORIGIN
    for y in range(top, top + config.RADAR_SIZE):
        for x in range(left, left + config.RADAR_SIZE):
            pixel = surface.get_at((x, y))
            if (pixel.r, pixel.g, pixel.b) == colour:
                return x, y
    return None


def test_radar_scale_derives_from_the_world(window):
    assert config.WORLD[0] // config.RADAR_SIZE == config.RADAR_SCALE


def test_a_player_at_the_world_origin_sits_at_the_radar_origin(display):
    display.fill(config.BLACK)

    RadarScreen().draw(display, 0, 0)

    assert blip_at(display, config.RADAR_PLAYER) == config.RADAR_ORIGIN


def test_a_player_at_the_far_corner_sits_at_the_radar_corner(display):
    display.fill(config.BLACK)
    far = config.WORLD[0] - config.RADAR_SCALE

    RadarScreen().draw(display, far, far)

    x, y = blip_at(display, config.RADAR_PLAYER)
    left, top = config.RADAR_ORIGIN
    assert x == left + config.RADAR_SIZE - 1
    assert y == top + config.RADAR_SIZE - 1


def test_a_zombie_shows_on_the_radar_where_it_stands(display, window, cash):
    display.fill(config.BLACK)
    zombie = Zombie(window, cash)
    zombie.set_position(1000, 2000)

    RadarScreen().update_zom(display, zombie)

    left, top = config.RADAR_ORIGIN
    assert blip_at(display, config.RADAR_ZOMBIE) == (
        left + 1000 // config.RADAR_SCALE,
        top + 2000 // config.RADAR_SCALE,
    )


def test_entities_read_their_tunables_from_config(window, cash):
    assert Zombie(window, cash).zombie_speed == config.ZOMBIE_SPEED
    assert Zombie(window, cash).zombie_health == config.ZOMBIE_HEALTH
    assert Human(window).health == config.PLAYER_HEALTH
    assert GunData(window).clip_size == config.CLIP_SIZE
    assert GunData(window).ammo_amount == config.RESERVE_SIZE
    assert Shot(0, 0, 1, 0).damage == config.BULLET_DAMAGE


def test_the_first_wave_uses_the_configured_base(window, cash):
    group = pygame.sprite.Group()

    WaveSystem(window, group, cash)

    assert len(group) == config.WAVE_BASE


def test_zombies_spawn_outside_the_spawn_area(window, cash):
    width, height = config.SPAWN_AREA

    for _ in range(40):
        x, y = Zombie(window, cash).get_position()
        assert x < 0 or x > width or y < 0 or y > height
