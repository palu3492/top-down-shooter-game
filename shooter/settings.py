"""Settings the player can change, and the file they live in.

`config` is import-time constants; settings are mutable state that outlives a
session. This is the bridge: defaults come from `config`, values come from the
player, and applying a setting writes it back onto `config` so the seventeen
existing read sites keep working untouched.

The hard part is not storage, it is honesty about *when* a change takes effect.
Every setting declares that, and `tests/test_settings.py` checks the declaration
against what the game actually does rather than trusting it.
"""

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from shooter import config

LIVE = "live"
NEW_ENTITIES = "new entities"
BOOT = "boot"

APP_DIRECTORY = "top-down-shooter"
FILE_NAME = "settings.json"


class InvalidSettingError(ValueError):
    """A value that cannot be stored under this name."""


def settings_path():
    """The platform's own place for user configuration, never the repo."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home())
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_DIRECTORY / FILE_NAME


@dataclass(frozen=True)
class Setting:
    """One tunable, and the promise about when changing it is felt."""

    name: str
    applies: str
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple | None = None

    @property
    def default(self):
        return getattr(config, self.name)

    def clean(self, value):
        default = self.default

        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise InvalidSettingError(f"{self.name} is on or off, got {value!r}")
            return value

        if isinstance(default, tuple) and isinstance(value, list):
            value = tuple(value)

        if self.choices is not None:
            if value not in self.choices:
                raise InvalidSettingError(f"{self.name} has no option {value!r}")
            return value

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidSettingError(f"{self.name} is a number, got {value!r}")

        value = type(default)(value)
        if self.minimum is not None and value < self.minimum:
            raise InvalidSettingError(
                f"{self.name} is at least {self.minimum}, got {value}"
            )
        if self.maximum is not None and value > self.maximum:
            raise InvalidSettingError(
                f"{self.name} is at most {self.maximum}, got {value}"
            )
        return value


RESOLUTIONS = ((1080, 720), (1280, 720), (1600, 900), (1920, 1080), (2560, 1440))

CATALOGUE = (
    Setting("WINDOW", BOOT, choices=RESOLUTIONS),
    Setting("VSYNC", BOOT, minimum=0, maximum=1),
    Setting("FPS", LIVE, minimum=30, maximum=1000),
    Setting("DEV_TOOLS", LIVE),
    Setting("PLAYER_SPEED", LIVE, minimum=60, maximum=3000),
    Setting("PLAYER_HEALTH", LIVE, minimum=1.0, maximum=1000.0),
    Setting("PLAYER_REGEN", LIVE, minimum=0.0, maximum=100.0),
    Setting("ZOMBIE_DAMAGE", LIVE, minimum=0.0, maximum=100.0),
    Setting("KILL_REWARD", LIVE, minimum=0, maximum=10_000),
    Setting("WAVE_BASE", LIVE, minimum=1, maximum=100),
    Setting("WAVE_INTERVAL_SECONDS", LIVE, minimum=1.0, maximum=600.0),
    Setting("ZOMBIE_SPEED", NEW_ENTITIES, minimum=30, maximum=3000),
    Setting("ZOMBIE_HEALTH", NEW_ENTITIES, minimum=1.0, maximum=10_000.0),
    Setting("RELOAD_SECONDS", NEW_ENTITIES, minimum=0.1, maximum=30.0),
    Setting("STARTING_GRENADES", NEW_ENTITIES, minimum=0, maximum=99),
    Setting("STARTING_STUN_GRENADES", NEW_ENTITIES, minimum=0, maximum=99),
)


class Settings:
    """The values in force, and the file they are remembered in."""

    def __init__(self, path=None, catalogue=CATALOGUE):
        self.catalogue = {setting.name: setting for setting in catalogue}
        self.path = Path(path) if path else settings_path()
        self.booted = {}
        self.reset()

    def __getitem__(self, name):
        return self.values[name]

    def __contains__(self, name):
        return name in self.catalogue

    def setting(self, name):
        if name not in self.catalogue:
            raise InvalidSettingError(f"there is no setting called {name!r}")
        return self.catalogue[name]

    def set(self, name, value):
        self.values[name] = self.setting(name).clean(value)

    def reset(self):
        self.values = {
            name: setting.default for name, setting in self.catalogue.items()
        }

    def load(self):
        """Take what the file offers; return the names it got wrong.

        A missing, unreadable or corrupt file is not an error -- it is a player
        who has never opened settings, and they get the defaults.
        """
        self.reset()
        try:
            stored = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return ()
        if not isinstance(stored, dict):
            return ()

        rejected = []
        for name, value in stored.items():
            try:
                self.set(name, value)
            except InvalidSettingError:
                rejected.append(name)
        return tuple(sorted(rejected))

    def save(self):
        """Written beside the target and moved into place, so an interrupted
        save leaves the previous settings rather than half a file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(handle, "w") as opened:
                json.dump(self.values, opened, indent=2, sort_keys=True)
            os.replace(temporary, self.path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def apply_at_startup(self, target=config):
        """Nothing has read `config` yet, so boot-only settings land too."""
        for name, value in self.values.items():
            setattr(target, name, value)
        self.booted = dict(self.values)

    def apply(self, target=config):
        """Write everything that can take effect now; name what cannot.

        The returned names are the boot-only settings that no longer match what
        the running game started with -- what AT24 warns about.
        """
        waiting = []
        for name, value in self.values.items():
            if self.catalogue[name].applies == BOOT:
                if value != self.booted.get(name, self.catalogue[name].default):
                    waiting.append(name)
                continue
            setattr(target, name, value)
        return tuple(sorted(waiting))
