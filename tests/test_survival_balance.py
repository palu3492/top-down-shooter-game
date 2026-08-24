import pytest

from shooter.survival_balance import SurvivalBalance, load_survival_balance
from shooter.modes.zombie_survival.mode import SurvivalMode


def test_profile_loads_editable_values_without_affecting_other_modes(tmp_path):
    profile = tmp_path / "survival.toml"
    profile.write_text("walker_speed = 180\nstarting_reserve = 12\n")

    balance = load_survival_balance(profile)

    assert balance.walker_speed == 180
    assert balance.starting_reserve == 12
    assert balance.runner_speed == SurvivalBalance().runner_speed


def test_profile_includes_spawn_pacing_and_rejects_an_empty_burst():
    balance = load_survival_balance()

    assert balance.spawn_burst_size == 2
    assert balance.spawn_burst_interval_seconds == 1
    assert balance.spawn_activation_delay_seconds == 0.75
    with pytest.raises(ValueError, match="burst size"):
        SurvivalBalance(spawn_burst_size=0)


def test_mode_uses_profile_weapon_damage_and_cooldowns():
    mode = SurvivalMode(
        balance=SurvivalBalance(
            pistol_damage=21,
            pistol_cooldown_seconds=0.5,
            smg_damage=15,
            smg_cooldown_seconds=0.1,
        )
    )

    assert mode.pistol.damage == 21
    assert mode.pistol.rate == 2
    assert mode.smg.damage == 15
    assert mode.smg.rate == 10
