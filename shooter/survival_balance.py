"""Editable, mode-owned balance values for a Survival run."""

from dataclasses import dataclass, fields
from pathlib import Path
import tomllib


BALANCE_PATH = Path(__file__).parents[1] / "balance" / "survival.toml"


@dataclass(frozen=True, slots=True)
class SurvivalBalance:
    walker_speed: float = 240
    runner_speed: float = 380
    breaker_speed: float = 220
    starting_magazine: int = 30
    starting_reserve: int = 30
    kill_reward: int = 50
    health_regeneration_per_second: float = 0.75
    initial_preparation_seconds: float = 10
    preparation_seconds: float = 25
    spawn_burst_size: int = 2
    spawn_burst_interval_seconds: float = 1.0
    spawn_activation_delay_seconds: float = 0.75

    def __post_init__(self):
        if min(self.walker_speed, self.runner_speed, self.breaker_speed) <= 0:
            raise ValueError("enemy speeds must be positive")
        if min(self.starting_magazine, self.starting_reserve, self.kill_reward) < 0:
            raise ValueError("ammo and rewards cannot be negative")
        if min(
            self.initial_preparation_seconds,
            self.preparation_seconds,
            self.health_regeneration_per_second,
            self.spawn_burst_interval_seconds,
            self.spawn_activation_delay_seconds,
        ) < 0:
            raise ValueError("preparation times cannot be negative")
        if self.spawn_burst_size < 1:
            raise ValueError("spawn burst size must be positive")


def load_survival_balance(path=BALANCE_PATH):
    """Load only recognised values, so future profile fields stay non-breaking."""
    with Path(path).open("rb") as profile:
        values = tomllib.load(profile)
    allowed = {field.name for field in fields(SurvivalBalance)}
    selected = {key: value for key, value in values.items() if key in allowed}
    return SurvivalBalance(**selected)


def save_survival_balance(balance, path=BALANCE_PATH):
    lines = (
        "# Zombie Survival tuning profile. Start a fresh match after saving.\n",
        f"walker_speed = {balance.walker_speed:g}\n",
        f"runner_speed = {balance.runner_speed:g}\n",
        f"breaker_speed = {balance.breaker_speed:g}\n",
        f"starting_magazine = {balance.starting_magazine}\n",
        f"starting_reserve = {balance.starting_reserve}\n",
        f"kill_reward = {balance.kill_reward}\n",
        "health_regeneration_per_second = "
        f"{balance.health_regeneration_per_second:g}\n",
        f"initial_preparation_seconds = {balance.initial_preparation_seconds:g}\n",
        f"preparation_seconds = {balance.preparation_seconds:g}\n",
        f"spawn_burst_size = {balance.spawn_burst_size}\n",
        "spawn_burst_interval_seconds = "
        f"{balance.spawn_burst_interval_seconds:g}\n",
        "spawn_activation_delay_seconds = "
        f"{balance.spawn_activation_delay_seconds:g}\n",
    )
    Path(path).write_text("".join(lines))
