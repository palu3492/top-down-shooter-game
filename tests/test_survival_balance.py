import pytest

from shooter.survival_balance import SurvivalBalance, load_survival_balance


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
