"""Initial, repeatable balance targets for the first authored Survival run."""

from shooter.map_definition import load_tmx_definition
from shooter.modes.zombie_survival.mode import DEFAULT_WAVE_PLAN
from shooter.survival_balance import load_survival_balance


def test_first_five_waves_create_intentional_preparation_purchase_choices():
    definition = load_tmx_definition("Assets/Maps/world_1/world_1.tmx")
    balance = load_survival_balance()
    prices = {
        interaction.interaction_id: int(dict(interaction.properties)["price"])
        for interaction in definition.interactions
    }
    rewards = {
        wave: sum(count for _, count in DEFAULT_WAVE_PLAN.composition(wave))
        * balance.kill_reward
        for wave in range(1, 6)
    }

    assert rewards == {1: 250, 2: 350, 3: 550, 4: 700, 5: 900}
    assert prices == {
        "camp-smg": 450,
        "camp-ammo": 250,
        "camp-health-pack": 150,
        "camp-armor": 400,
        "camp-pistol": 150,
    }
    # Wave one buys the required first firearm, but not recovery alongside it.
    assert rewards[1] >= prices["camp-pistol"]
    assert rewards[1] < prices["camp-pistol"] + prices["camp-health-pack"]
    # After pistol purchase, wave two enables the SMG or a recovery/ammo choice.
    cash_after_pistol_then_wave_two = (
        rewards[1] - prices["camp-pistol"] + rewards[2]
    )
    assert cash_after_pistol_then_wave_two == prices["camp-smg"]
    assert cash_after_pistol_then_wave_two >= (
        prices["camp-ammo"] + prices["camp-health-pack"]
    )
    # By wave three, armor becomes an achievable added layer of protection.
    assert sum(rewards[wave] for wave in range(1, 4)) >= prices["camp-armor"]
