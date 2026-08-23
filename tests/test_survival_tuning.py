"""Initial, repeatable balance targets for the first authored Survival run."""

from shooter import config
from shooter.map_definition import load_tmx_definition
from shooter.modes.zombie_survival.mode import DEFAULT_WAVE_PLAN


def test_first_five_waves_create_intentional_preparation_purchase_choices():
    definition = load_tmx_definition("Assets/Maps/world_1/world_1.tmx")
    prices = {
        interaction.interaction_id: int(dict(interaction.properties)["price"])
        for interaction in definition.interactions
    }
    rewards = {
        wave: sum(count for _, count in DEFAULT_WAVE_PLAN.composition(wave))
        * config.KILL_REWARD
        for wave in range(1, 6)
    }

    assert rewards == {1: 250, 2: 350, 3: 550, 4: 700, 5: 900}
    assert prices == {
        "camp-smg": 500,
        "camp-ammo": 250,
        "camp-health": 300,
        "camp-armor": 400,
    }
    # Wave one funds one ammo refill, but no larger recovery or weapon purchase.
    assert rewards[1] == prices["camp-ammo"]
    assert rewards[1] < min(prices["camp-smg"], prices["camp-health"])
    # By wave two, the player chooses between saving for an SMG and recovery.
    assert rewards[1] + rewards[2] >= prices["camp-smg"]
    # By wave three, armor becomes an achievable added layer of protection.
    assert sum(rewards[wave] for wave in range(1, 4)) >= prices["camp-armor"]
