import pygame

from shooter.survival_balance import SurvivalBalance, load_survival_balance
from shooter.ui.survival_tuner import SurvivalTuner


def test_tuner_adjusts_and_saves_the_next_run_profile(tmp_path):
    tuner = SurvivalTuner(SurvivalBalance(walker_speed=240))
    tuner.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
    assert tuner.balance.walker_speed == 220

    import shooter.ui.survival_tuner as module

    original = module.save_survival_balance
    module.save_survival_balance = lambda balance: original(
        balance, tmp_path / "run.toml"
    )
    try:
        tuner.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s))
    finally:
        module.save_survival_balance = original
    assert load_survival_balance(tmp_path / "run.toml").walker_speed == 220
