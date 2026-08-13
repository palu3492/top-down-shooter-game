import pygame

from shooter.demos.depth_demo import ARENA, DemoScene, DemoState, Zombie
from shooter.demos.environment_map import EnvironmentProp


def test_player_moves_and_stays_inside_fixed_arena():
    scene = DemoScene(spawn_interval=999)
    start = scene.player.copy()
    scene.update(0.05, pygame.Vector2(1, 0))
    assert scene.player.x > start.x
    for _ in range(300):
        scene.move_player(pygame.Vector2(1, 1), 0.05)
    assert ARENA.collidepoint(scene.player)


def test_player_does_not_walk_through_obstacle_footprint():
    scene = DemoScene(spawn_interval=999)
    obstacle = scene.obstacles[0]
    scene.player.update(
        obstacle.footprint.left - scene.player_radius - 2, obstacle.footprint.centery
    )
    for _ in range(30):
        scene.move_player(pygame.Vector2(1, 0), 0.02)
    assert scene.player.x < obstacle.footprint.left


def test_zombies_spawn_at_edges_and_approach_player():
    scene = DemoScene(seed=1, spawn_interval=999)
    zombie = scene.spawn_zombie()
    assert zombie.position.x in (12, 1068) or zombie.position.y in (12, 708)
    before = zombie.position.distance_to(scene.player)
    scene.update(0.05)
    assert zombie.position.distance_to(scene.player) < before


def test_shot_removes_zombie_and_counts_kill():
    scene = DemoScene(spawn_interval=999)
    scene.zombies.append(Zombie(scene.player + pygame.Vector2(75, 0), speed=0))
    assert scene.shoot(scene.player + pygame.Vector2(200, 0))
    for _ in range(10):
        scene.update(0.02)
    assert not scene.zombies
    assert scene.kills == 1


def test_depth_order_uses_ground_anchor():
    scene = DemoScene(spawn_interval=999)
    scene.player.y = 300
    behind = Zombie(pygame.Vector2(400, 250))
    ahead = Zombie(pygame.Vector2(400, 350))
    scene.zombies = [ahead, behind]
    ordered = scene.depth_order()
    assert ordered.index(behind) < ordered.index("player") < ordered.index(ahead)
    assert all(
        isinstance(item, (EnvironmentProp, Zombie)) or item == "player"
        for item in ordered
    )


def test_presentation_map_is_dense_and_uses_the_same_collision_footprints():
    scene = DemoScene(spawn_interval=999)

    assert len(scene.obstacles) >= 20
    assert len(scene.environment.decals) >= 40
    assert scene.flow.blocked


def test_draw_renders_to_logical_surface():
    scene = DemoScene(spawn_interval=999)
    surface = pygame.Surface((1080, 720))
    scene.draw(surface)
    assert surface.get_at((0, 0)) != pygame.Color(0, 0, 0, 255)


def test_presentable_loop_waits_for_start_and_can_be_restarted():
    scene = DemoScene(start_ready=True, encounter_duration=0.1, spawn_interval=999)
    scene.update(0.05)
    assert scene.state == DemoState.READY
    assert scene.elapsed == 0
    scene.start()
    scene.update(0.05)
    scene.update(0.05)
    assert scene.state == DemoState.WON
    scene.restart()
    assert scene.state == DemoState.PLAYING
    assert scene.elapsed == 0


def test_ammo_reload_and_pickups():
    scene = DemoScene(spawn_interval=999)
    scene.ammo = 1
    assert scene.shoot(scene.player + pygame.Vector2(100, 0))
    assert scene.ammo == 0
    assert scene.reload()
    for _ in range(18):
        scene.update(0.05)
    assert scene.ammo == scene.magazine_size
    pickup = scene.spawn_pickup("health")
    pickup.position = scene.player.copy()
    scene.player_health = 20
    scene.update(0.01)
    assert scene.player_health == 55
    assert not scene.pickups


def test_living_zombie_cap_is_enforced():
    scene = DemoScene(spawn_interval=0.01, max_zombies=3)
    for _ in range(20):
        scene.update(0.05)
    assert len(scene.zombies) <= 3
