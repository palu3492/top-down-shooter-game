import pytest

from shooter import config

from shooter.ui.hud import GunData


@pytest.fixture
def gun(window):
    return GunData(window)


def test_starts_with_a_full_clip_and_two_spares(gun):
    assert (gun.clip_size, gun.ammo_amount) == (60, 120)


def test_firing_consumes_one_round(gun):
    assert gun.shooting_bullet() is None
    assert (gun.clip_size, gun.ammo_amount) == (59, 120)


def test_emptying_the_clip_triggers_an_automatic_reload(gun):
    for _ in range(59):
        assert gun.shooting_bullet() is None
    assert gun.clip_size == 1

    assert gun.shooting_bullet() == "reload"
    assert (gun.clip_size, gun.ammo_amount) == (60, 60)


def test_firing_every_round_ends_in_no_ammo(gun):
    fired = 0
    while gun.shooting_bullet() != "no ammo":
        fired += 1
        assert fired < 500, "never ran dry"

    assert (gun.clip_size, gun.ammo_amount) == (0, 0)
    assert fired == 180


def test_manual_reload_tops_up_a_partial_clip(gun):
    gun.clip_size = 30

    assert gun.manual_reload() == "reload"
    assert (gun.clip_size, gun.ammo_amount) == (60, 90)


def test_manual_reload_with_too_little_reserve_takes_what_is_left(gun):
    gun.clip_size = 30
    gun.ammo_amount = 10

    assert gun.manual_reload() == "reload"
    assert (gun.clip_size, gun.ammo_amount) == (40, 0)


def test_manual_reload_on_an_empty_reserve_and_partial_clip_is_a_no_op(gun):
    gun.clip_size = 30
    gun.ammo_amount = 0

    assert gun.manual_reload() is None
    assert (gun.clip_size, gun.ammo_amount) == (30, 0)


def test_manual_reload_with_nothing_left_reports_no_ammo(gun):
    gun.clip_size = 0
    gun.ammo_amount = 0

    assert gun.manual_reload() == "no ammo"


def test_reload_counts_down_then_clears(gun):
    dt = config.SIM_DT
    assert gun.reload_seconds == config.RELOAD_SECONDS

    for _ in range(int(config.RELOAD_SECONDS * config.SIM_HZ)):
        assert gun.reloading(dt) == "reload"

    assert gun.reloading(dt) is None
    assert gun.reload_seconds == config.RELOAD_SECONDS


def test_two_guns_do_not_share_ammo(gun, window):
    other = GunData(window)
    gun.shooting_bullet()

    assert other.clip_size == 60
