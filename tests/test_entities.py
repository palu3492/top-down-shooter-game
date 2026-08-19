import pytest

from shooter import config

from shooter.entities.player import IDLE_ANIMATION_FPS, KNIFE_ATTACK_FPS, Human
from shooter.entities.zombie import Zombie


@pytest.fixture
def human(window):
    return Human(window)


@pytest.fixture
def zombie(window, cash):
    return Zombie(window, cash)


def test_human_starts_at_full_health(human):
    assert human.get_health() == 100


def test_human_survives_a_hit(human):
    assert human.remove_health(30) is False
    assert human.get_health() == 70


def test_human_dies_when_health_runs_out(human):
    assert human.remove_health(100) is True


def test_human_health_never_reports_negative(human):
    human.remove_health(250)

    assert human.get_health() == 0


def test_human_regenerates_while_animating(human):
    human.remove_health(10)
    before = human.health
    human.update_anim("IDLE")

    assert human.health > before


def test_human_regen_stops_at_full(human):
    for _ in range(100):
        human.update_anim("IDLE")

    assert human.get_health() == 100


def test_two_humans_have_separate_health(human, window):
    human.remove_health(50)

    assert Human(window).get_health() == 100


def test_zombie_survives_a_bullet(zombie):
    assert zombie.remove_health(20) is False


def test_killing_a_zombie_pays_out(zombie, cash):
    assert zombie.remove_health(100) is True
    assert cash.received == [50]


def test_a_zombie_only_pays_out_once(zombie, cash):
    zombie.remove_health(100)
    zombie.remove_health(100)
    zombie.remove_health(100)

    assert cash.received == [50]


def test_zombie_spawns_outside_the_play_area(zombie, window):
    x, y = zombie.get_position()

    assert x < 0 or x > window[0] or y < 0 or y > window[1]


def test_two_zombies_have_separate_health(zombie, window, cash):
    zombie.remove_health(50)

    assert Zombie(window, cash).zombie_health == 100


def test_stun_slows_the_zombie_then_wears_off(zombie):
    original = zombie.zombie_speed
    zombie.remove_speed(config.STUN_SPEED)

    assert zombie.zombie_speed == config.STUN_SPEED
    for _ in range(int(config.STUN_SECONDS * config.SIM_HZ) + 2):
        zombie.zombie_speed_timer(config.SIM_DT)

    assert zombie.zombie_speed == original


def test_player_animation_advances_through_its_frames(human):
    seen = {id(human.image)}
    for _ in range(5):
        human.update_anim("MOVE")
        seen.add(id(human.image))

    assert len(seen) > 1


def test_idle_animation_advances(human):
    human.update_anim("IDLE", dt=1 / IDLE_ANIMATION_FPS)
    first = human.image
    human.update_anim("IDLE", dt=1 / IDLE_ANIMATION_FPS)

    assert human.image is not first


def test_idle_animation_waits_for_its_frame_interval(human):
    first = human.image

    human.update_anim("IDLE", dt=(1 / IDLE_ANIMATION_FPS) - 0.001)

    assert human.image is first


def test_knife_attack_lunges_out_and_returns_before_idle(human):
    attack = human.frames["SHOOT"]
    frame_time = 1 / KNIFE_ATTACK_FPS

    seen = []
    human.update_anim("SHOOT", dt=0)
    seen.append(human.image)
    for _ in range(len(attack) - 1):
        human.update_anim("IDLE", dt=frame_time)
        seen.append(human.image)

    assert seen == list(attack)
    human.update_anim("IDLE")
    assert human.type == "IDLE"


def test_knife_attack_does_not_disappear_on_the_next_simulation_tick(human):
    human.update_anim("SHOOT", dt=config.SIM_DT)
    first = human.image

    human.update_anim("IDLE", dt=config.SIM_DT)

    assert human.type == "SHOOT"
    assert human.image is first


@pytest.mark.parametrize("weapon_id", ("knife", "m16", "smg", "shotgun", "sniper"))
def test_player_uses_the_equipped_weapons_animation(human, weapon_id):
    human.update_anim("IDLE", weapon_id=weapon_id)

    assert human.weapon_id == weapon_id
    assert human.frames is human.animation_sets[weapon_id]


def test_zombie_animation_advances(zombie):
    seen = {id(zombie.image)}
    for _ in range(5):
        zombie.update_anim("MOVE")
        seen.add(id(zombie.image))

    assert len(seen) > 1


def test_zombie_hitbox_stays_stable_between_different_sized_poses(zombie):
    zombie.update_anim("MOVE")
    moving = zombie.rect.size
    assert moving == config.ZOMBIE_SIZE

    zombie.update_anim("ATTACK")
    assert zombie.rect.size == moving


def test_zombie_body_does_not_swell_when_attacking(zombie):
    """Attack art comes from a larger rig and needs its own source correction."""
    tallest_walk_pose = max(
        frame.get_bounding_rect().height for frame in zombie.frames["MOVE"]
    )
    tallest_attack_pose = max(
        frame.get_bounding_rect().height for frame in zombie.frames["ATTACK"]
    )

    assert tallest_attack_pose <= tallest_walk_pose


def test_changing_pose_does_not_teleport_the_zombie(zombie):
    zombie.rect.topleft = (100, 200)
    zombie.update_anim("ATTACK")

    assert zombie.rect.topleft == (100, 200)


def test_rotation_keeps_the_player_centred(human):
    centre = human.rect.center

    for angle in (0, 37, 90, 180, 271):
        human.update_anim("MOVE")
        human.rot_center(angle)

        assert human.rect.center == centre


def test_rotation_no_longer_desyncs_image_from_rect(human):
    human.rot_center(45)

    assert human.rect.size == human.image.get_size()
