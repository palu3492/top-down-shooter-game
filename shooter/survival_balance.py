"""Editable, mode-owned balance values for a Survival run."""

from dataclasses import dataclass, fields
from pathlib import Path
import tomllib


BALANCE_PATH = Path(__file__).parents[1] / "balance" / "survival.toml"


@dataclass(frozen=True, slots=True)
class SurvivalBalance:
    player_speed: float = 300
    player_max_health: float = 100
    pistol_damage: float = 18
    pistol_cooldown_seconds: float = 0.25
    pistol_reload_seconds: float = 1
    smg_damage: float = 22
    smg_cooldown_seconds: float = 1 / 12
    smg_reload_seconds: float = 1.2
    smg_spread_degrees: float = 0
    tool_damage: float = 75
    tool_cooldown_seconds: float = 1 / 3
    walker_speed: float = 240
    runner_speed: float = 380
    breaker_speed: float = 220
    enemy_speed_variation_fraction: float = 0.05
    walker_health: float = 100
    runner_health: float = 70
    breaker_health: float = 260
    contact_damage_per_second: float = 6
    breaker_barricade_damage_multiplier: float = 4
    starting_magazine: int = 30
    starting_reserve: int = 30
    kill_reward: int = 50
    health_regeneration_per_second: float = 0.75
    initial_preparation_seconds: float = 10
    preparation_seconds: float = 25
    spawn_burst_size: int = 2
    spawn_burst_interval_seconds: float = 1.0
    spawn_activation_delay_seconds: float = 0.75
    walker_wave_one_count: int = 5
    walker_wave_growth: int = 2
    runner_starts_at_wave: int = 3
    runner_wave_count: int = 2
    runner_wave_growth: int = 1
    breaker_starts_at_wave: int = 5
    breaker_wave_count: int = 1

    def __post_init__(self):
        if min(
            self.player_speed,
            self.walker_speed,
            self.runner_speed,
            self.breaker_speed,
        ) <= 0:
            raise ValueError("movement speeds must be positive")
        if self.player_max_health <= 0:
            raise ValueError("player health must be positive")
        if not 0 <= self.enemy_speed_variation_fraction < 1:
            raise ValueError("enemy speed variation must be between zero and one")
        if min(self.walker_health, self.runner_health, self.breaker_health) <= 0:
            raise ValueError("enemy health must be positive")
        if min(self.pistol_damage, self.smg_damage) <= 0:
            raise ValueError("weapon damage must be positive")
        if min(self.pistol_cooldown_seconds, self.smg_cooldown_seconds) <= 0:
            raise ValueError("weapon cooldowns must be positive")
        if min(self.pistol_reload_seconds, self.smg_reload_seconds) < 0:
            raise ValueError("weapon reload times cannot be negative")
        if self.smg_spread_degrees < 0:
            raise ValueError("weapon spread cannot be negative")
        if min(self.tool_damage, self.tool_cooldown_seconds) <= 0:
            raise ValueError("tool values must be positive")
        if min(
            self.contact_damage_per_second,
            self.breaker_barricade_damage_multiplier,
        ) < 0:
            raise ValueError("enemy damage values cannot be negative")
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
        if min(
            self.walker_wave_one_count,
            self.walker_wave_growth,
            self.runner_starts_at_wave,
            self.runner_wave_count,
            self.runner_wave_growth,
            self.breaker_starts_at_wave,
            self.breaker_wave_count,
        ) < 0:
            raise ValueError("wave configuration cannot be negative")


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
        f"player_speed = {balance.player_speed:g}\n",
        f"player_max_health = {balance.player_max_health:g}\n",
        f"pistol_damage = {balance.pistol_damage:g}\n",
        f"pistol_cooldown_seconds = {balance.pistol_cooldown_seconds:g}\n",
        f"pistol_reload_seconds = {balance.pistol_reload_seconds:g}\n",
        f"smg_damage = {balance.smg_damage:g}\n",
        f"smg_cooldown_seconds = {balance.smg_cooldown_seconds:g}\n",
        f"smg_reload_seconds = {balance.smg_reload_seconds:g}\n",
        f"smg_spread_degrees = {balance.smg_spread_degrees:g}\n",
        f"tool_damage = {balance.tool_damage:g}\n",
        f"tool_cooldown_seconds = {balance.tool_cooldown_seconds:g}\n",
        f"walker_speed = {balance.walker_speed:g}\n",
        f"runner_speed = {balance.runner_speed:g}\n",
        f"breaker_speed = {balance.breaker_speed:g}\n",
        "enemy_speed_variation_fraction = "
        f"{balance.enemy_speed_variation_fraction:g}\n",
        f"walker_health = {balance.walker_health:g}\n",
        f"runner_health = {balance.runner_health:g}\n",
        f"breaker_health = {balance.breaker_health:g}\n",
        f"contact_damage_per_second = {balance.contact_damage_per_second:g}\n",
        "breaker_barricade_damage_multiplier = "
        f"{balance.breaker_barricade_damage_multiplier:g}\n",
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
        f"walker_wave_one_count = {balance.walker_wave_one_count}\n",
        f"walker_wave_growth = {balance.walker_wave_growth}\n",
        f"runner_starts_at_wave = {balance.runner_starts_at_wave}\n",
        f"runner_wave_count = {balance.runner_wave_count}\n",
        f"runner_wave_growth = {balance.runner_wave_growth}\n",
        f"breaker_starts_at_wave = {balance.breaker_starts_at_wave}\n",
        f"breaker_wave_count = {balance.breaker_wave_count}\n",
    )
    Path(path).write_text("".join(lines))
