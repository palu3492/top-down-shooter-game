import pytest

from shooter import config

from shooter.entities.player import Human
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


def test_killing_a_zombie_does_not_own_the_reward_policy(zombie, cash):
    assert zombie.remove_health(100) is True
    assert cash.received == []


def test_repeated_zombie_damage_has_no_reward_side_effect(zombie, cash):
    zombie.remove_health(100)
    zombie.remove_health(100)
    zombie.remove_health(100)

    assert cash.received == []


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


@pytest.mark.parametrize("weapon_id", ("knife", "m16", "smg", "shotgun", "sniper"))
@pytest.mark.parametrize("action", ("IDLE", "MOVE", "SHOOT"))
def test_player_uses_one_image_for_every_action_and_weapon(human, weapon_id, action):
    human.update_anim(action, weapon_id=weapon_id)

    assert human.image is human.base_image


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
