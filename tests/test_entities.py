import pytest

from conftest import WINDOW, FakeCash
from shooter.entities.player import Human
from shooter.entities.zombie import Zombie


@pytest.fixture
def human():
    return Human(WINDOW)


@pytest.fixture
def cash():
    return FakeCash()


@pytest.fixture
def zombie(cash):
    return Zombie(WINDOW, cash)


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


def test_two_humans_have_separate_health(human):
    human.remove_health(50)

    assert Human(WINDOW).get_health() == 100


def test_zombie_survives_a_bullet(zombie):
    assert zombie.remove_health(20) is False


def test_killing_a_zombie_pays_out(zombie, cash):
    assert zombie.remove_health(100) is True
    assert cash.received == [50]


def test_zombie_spawns_outside_the_play_area(zombie):
    x, y = zombie.get_posistion()

    assert x < 0 or x > 1080 or y < 0 or y > 720


def test_two_zombies_have_separate_health(zombie, cash):
    zombie.remove_health(50)

    assert Zombie(WINDOW, cash).zombie_health == 100


def test_stun_slows_the_zombie_then_wears_off(zombie):
    original = zombie.zombie_speed
    zombie.remove_speed(3)

    assert zombie.zombie_speed == 3
    for _ in range(zombie.stun_timer + 1):
        zombie.zombie_speed_timer()

    assert zombie.zombie_speed == original


def test_player_animation_advances_through_its_frames(human):
    seen = {id(human.image)}
    for _ in range(5):
        human.update_anim("MOVE")
        seen.add(id(human.image))

    assert len(seen) > 1


@pytest.mark.xfail(strict=True, reason="idle is pinned to frame 0 and never advances")
def test_idle_animation_should_advance(human):
    human.update_anim("IDLE")
    first = human.image
    human.update_anim("IDLE")

    assert human.image is not first
