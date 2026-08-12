"""The settings store.

Storage is the easy half and is tested here for completeness. The half worth
having is the second section: every setting claims when a change is felt, and
those claims are checked against real game objects rather than believed.
"""

import ast
import json
from pathlib import Path

import pygame
import pytest

from shooter import config, game
from shooter.entities.player import Human
from shooter.entities.zombie import Zombie
from shooter.settings import (
    BOOT,
    CATALOGUE,
    LIVE,
    NEW_ENTITIES,
    InvalidSettingError,
    Setting,
    Settings,
    settings_path,
)
from shooter.ui.hud import Cash, GunData


@pytest.fixture
def store(tmp_path):
    return Settings(path=tmp_path / "settings.json")


@pytest.fixture
def spare(monkeypatch):
    """A stand-in for the config module, so applying cannot leak between tests."""

    class Spare:
        pass

    spare = Spare()
    for setting in CATALOGUE:
        setattr(spare, setting.name, setting.default)
    return spare


def test_defaults_come_from_config(store):
    for setting in CATALOGUE:
        assert store[setting.name] == getattr(config, setting.name)


def test_every_default_survives_its_own_validation():
    """A bound that excludes the shipped value would break the first save."""
    for setting in CATALOGUE:
        assert setting.clean(setting.default) == setting.default


def test_a_setting_can_be_changed_and_read_back(store):
    store.set("FPS", 144)
    assert store["FPS"] == 144


def test_an_unknown_name_is_refused(store):
    with pytest.raises(InvalidSettingError):
        store.set("NOT_A_SETTING", 1)


def test_a_value_out_of_range_is_refused(store):
    with pytest.raises(InvalidSettingError):
        store.set("FPS", 5)
    with pytest.raises(InvalidSettingError):
        store.set("FPS", 100_000)


def test_a_value_of_the_wrong_shape_is_refused(store):
    with pytest.raises(InvalidSettingError):
        store.set("FPS", "fast")
    with pytest.raises(InvalidSettingError):
        store.set("DEV_TOOLS", 1)
    with pytest.raises(InvalidSettingError):
        store.set("WINDOW", (999, 999))


def test_a_number_is_not_accepted_as_a_switch(store):
    """`True` is an int in Python, so a switch has to reject numbers itself."""
    with pytest.raises(InvalidSettingError):
        store.set("DEV_TOOLS", 0)
    store.set("DEV_TOOLS", False)
    assert store["DEV_TOOLS"] is False


def test_resetting_returns_every_default(store):
    store.set("FPS", 144)
    store.reset()
    assert store["FPS"] == config.FPS


def test_saving_then_loading_round_trips(store):
    store.set("FPS", 144)
    store.set("WINDOW", (1920, 1080))
    store.save()

    reopened = Settings(path=store.path)
    assert reopened.load() == ()
    assert reopened["FPS"] == 144
    assert reopened["WINDOW"] == (1920, 1080)


def test_a_tuple_survives_the_trip_through_json(store):
    store.set("WINDOW", (1600, 900))
    store.save()
    assert json.loads(store.path.read_text())["WINDOW"] == [1600, 900]

    reopened = Settings(path=store.path)
    reopened.load()
    assert reopened["WINDOW"] == (1600, 900)


def test_a_missing_file_is_not_an_error(tmp_path):
    store = Settings(path=tmp_path / "never" / "written.json")
    assert store.load() == ()
    assert store["FPS"] == config.FPS


def test_a_corrupt_file_falls_back_to_defaults(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{ not json at all")
    assert store.load() == ()
    assert store["FPS"] == config.FPS


def test_a_file_that_is_not_an_object_falls_back_to_defaults(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("[1, 2, 3]")
    assert store.load() == ()
    assert store["FPS"] == config.FPS


def test_bad_values_are_named_and_the_rest_still_load(store):
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        json.dumps({"FPS": 144, "PLAYER_SPEED": -5, "GONE_AWAY": True})
    )

    assert store.load() == ("GONE_AWAY", "PLAYER_SPEED")
    assert store["FPS"] == 144
    assert store["PLAYER_SPEED"] == config.PLAYER_SPEED


def test_an_interrupted_save_leaves_the_previous_settings(store, monkeypatch):
    store.set("FPS", 144)
    store.save()

    def die(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("json.dump", die)
    store.set("FPS", 60)
    with pytest.raises(OSError):
        store.save()

    reopened = Settings(path=store.path)
    reopened.load()
    assert reopened["FPS"] == 144
    assert list(store.path.parent.glob("*.tmp")) == []


def test_settings_live_outside_the_repository():
    path = settings_path()
    assert path.name == "settings.json"
    assert Path.cwd() not in path.parents


def test_every_setting_declares_when_it_applies():
    assert {setting.applies for setting in CATALOGUE} <= {LIVE, NEW_ENTITIES, BOOT}


def test_applying_writes_live_settings_through(store, spare):
    store.set("FPS", 144)
    assert store.apply(spare) == ()
    assert spare.FPS == 144


def test_applying_holds_boot_settings_back_and_names_them(store, spare):
    store.apply_at_startup(spare)
    store.set("VSYNC", not config.VSYNC)

    assert store.apply(spare) == ("VSYNC",)
    assert spare.VSYNC == config.VSYNC


def test_a_boot_setting_put_back_stops_being_pending(store, spare):
    store.apply_at_startup(spare)
    store.set("VSYNC", not config.VSYNC)
    store.set("VSYNC", config.VSYNC)
    assert store.apply(spare) == ()


def test_startup_applies_everything(store, spare):
    store.set("WINDOW", (1920, 1080))
    store.set("FPS", 144)
    store.apply_at_startup(spare)
    assert (spare.WINDOW, spare.FPS) == ((1920, 1080), 144)


LIVE_SETTINGS = [s.name for s in CATALOGUE if s.applies == LIVE]
NEW_ENTITY_SETTINGS = [s.name for s in CATALOGUE if s.applies == NEW_ENTITIES]


def test_a_live_setting_is_read_after_construction(window, monkeypatch):
    """PLAYER_HEALTH is the awkward one: captured as a starting value, but the
    regeneration cap is read live, so raising it does reach an existing player."""
    monkeypatch.setattr(config, "PLAYER_HEALTH", 100.0)
    human = Human(window)
    human.remove_health(50)

    monkeypatch.setattr(config, "PLAYER_HEALTH", 500.0)
    for _ in range(3000):
        human.health_regen(0.1)

    assert human.health == pytest.approx(500.0)


def test_a_new_entity_setting_leaves_existing_entities_alone(window, monkeypatch):
    monkeypatch.setattr(config, "ZOMBIE_SPEED", 360)
    before = Zombie(window, Cash())

    monkeypatch.setattr(config, "ZOMBIE_SPEED", 999)
    after = Zombie(window, Cash())

    assert (before.zombie_speed, after.zombie_speed) == (360, 999)


def test_new_entities_is_a_promise_about_new_ones_only(window, monkeypatch):
    """A stunned zombie re-reads the speed when the stun expires, so an existing
    one can pick up the new value. The guarantee is that new ones always do."""
    monkeypatch.setattr(config, "ZOMBIE_SPEED", 360)
    zombie = Zombie(window, Cash())

    monkeypatch.setattr(config, "ZOMBIE_SPEED", 999)
    zombie.remove_speed(config.STUN_SPEED)
    for _ in range(int(config.STUN_SECONDS * 60) + 5):
        zombie.zombie_speed_timer(1 / 60)

    assert zombie.zombie_speed == 999


def test_a_new_entity_setting_reaches_the_next_one_built(window, monkeypatch):
    monkeypatch.setattr(config, "RELOAD_SECONDS", 9.0)
    assert GunData(window).reload_seconds == 9.0


def test_a_boot_setting_is_only_read_at_startup():
    """VSYNC is read where the display is opened and nowhere else, which is what
    makes it honestly boot-only. WINDOW is live now and is read wherever the
    display is rebuilt, so it is no longer part of this guarantee."""
    source = Path(__file__).parent.parent / "shooter"
    reads = [
        f"{path.relative_to(source)}:{node.lineno}"
        for path in source.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Attribute)
        and node.attr == "VSYNC"
        and isinstance(node.value, ast.Name)
        and node.value.id == "config"
    ]
    assert len(reads) == 1, reads


def test_no_setting_is_frozen_into_another_name_at_import():
    """`BULLET_DAMAGE = config.BULLET_DAMAGE` at module or class level copies the
    value once and never looks again, so such a name cannot be a setting at all
    until its readers are rewired."""
    source = Path(__file__).parent.parent / "shooter"
    frozen = set()
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text())
        bodies = [tree] + [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        for body in bodies:
            for node in body.body:
                if not isinstance(node, ast.Assign):
                    continue
                value = node.value
                if (
                    isinstance(value, ast.Attribute)
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "config"
                ):
                    frozen.add(value.attr)

    assert frozen, "the guard found no import-time copies, so it is not working"
    assert frozen.isdisjoint({setting.name for setting in CATALOGUE}), (
        f"these are copied at import and would silently do nothing: "
        f"{sorted(frozen & {s.name for s in CATALOGUE})}"
    )


def test_the_catalogue_names_real_config_values():
    for setting in CATALOGUE:
        assert hasattr(config, setting.name), setting.name


def test_simulation_rate_is_not_a_setting():
    """AT16 bought determinism at a fixed rate; exposing it gives that away."""
    names = {setting.name for setting in CATALOGUE}
    assert names.isdisjoint({"SIM_HZ", "SIM_DT", "MAX_FRAME_SECONDS"})


def test_a_setting_with_choices_rejects_anything_else():
    setting = Setting("WINDOW", BOOT, choices=((1, 2), (3, 4)))
    assert setting.clean([1, 2]) == (1, 2)
    with pytest.raises(InvalidSettingError):
        setting.clean((9, 9))


def test_a_stored_value_reaches_the_running_game(
    straight_to_game, _settings_isolated, monkeypatch
):
    """The whole point: something written to disk changes how the game runs."""
    _settings_isolated.parent.mkdir(parents=True, exist_ok=True)
    _settings_isolated.write_text(json.dumps({"FPS": 144, "ZOMBIE_SPEED": 500}))

    seen = {}
    real_flip = pygame.display.flip

    def flip():
        seen.setdefault("FPS", config.FPS)
        seen.setdefault("ZOMBIE_SPEED", config.ZOMBIE_SPEED)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    game.game_loop()

    assert seen == {"FPS": 144, "ZOMBIE_SPEED": 500}


def test_a_corrupt_file_does_not_stop_the_game_starting(
    _settings_isolated, monkeypatch
):
    _settings_isolated.parent.mkdir(parents=True, exist_ok=True)
    _settings_isolated.write_text("{{{ garbage")

    seen = {}
    real_flip = pygame.display.flip

    def flip():
        seen.setdefault("FPS", config.FPS)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        real_flip()

    monkeypatch.setattr(pygame.display, "flip", flip)
    game.game_loop()

    assert seen["FPS"] == config.FPS
