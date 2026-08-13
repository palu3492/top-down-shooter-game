"""What the player has got through, remembered between sessions.

This is the small half of the campaign problem. *Progress* -- how far they have
reached, what they have finished, the best run so far -- is a handful of numbers
and AT23 already established how to keep them: validated JSON in the platform's
own config directory, written through a temporary file so an interrupted save
leaves the previous one.

*Mid-game serialisation* -- exact zombie positions, ammunition, where the wave
had got to -- is a far bigger commitment and is deliberately not here. A
checkpoint does not need it: reaching level four means level four can be started
again from its definition, which is a level number rather than a world.
"""

import json
import os
import tempfile
from pathlib import Path

from shooter import settings

FILE_NAME = "progress.json"

FIRST_LEVEL = 1


def progress_path():
    """Beside the settings, in the platform's own place for user data.

    Reached through the module rather than imported by name, so anything that
    redirects the settings -- the test suite does, to keep out of a developer's
    real files -- redirects this with it.
    """
    return settings.settings_path().with_name(FILE_NAME)


class Progress:
    """How far the player has got.

    `reached` is the furthest level they may start from; `completed` is what
    they have actually finished. They differ at the moment a level is won: the
    next one unlocks before it has been played.
    """

    def __init__(self, path=None, last_level=None):
        self.path = Path(path) if path else progress_path()
        self.last_level = last_level
        self.reset()

    def reset(self):
        self.reached = FIRST_LEVEL
        self.completed = ()

    @property
    def started(self):
        """Whether there is anything to come back to."""
        return self.reached > FIRST_LEVEL or bool(self.completed)

    @property
    def finished(self):
        """Every level there is, completed."""
        return self.last_level is not None and self.last_level in self.completed

    def record(self, number, unlocks=None):
        """Note a level as finished, and open the one after it.

        Nothing moves backwards: replaying an early level cannot take away a
        level already reached.
        """
        number = int(number)
        if number not in self.completed:
            self.completed = tuple(sorted((*self.completed, number)))
        following = self._unlocked_by(number) if unlocks is None else int(unlocks)
        if self.last_level is not None:
            following = min(following, self.last_level)
        self.reached = max(self.reached, following)

    def _unlocked_by(self, number):
        """Finishing a level opens the next, up to the last one there is."""
        following = number + 1
        if self.last_level is not None:
            following = min(following, self.last_level)
        return following

    def load(self):
        """Take what the file offers; return the keys it got wrong.

        A missing or corrupt file is not an error -- it is a player who has
        never finished a level, and they start at the beginning.
        """
        self.reset()
        try:
            stored = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return ()
        if not isinstance(stored, dict):
            return ()

        rejected = []
        if not self._take_completed(stored.get("completed", [])):
            rejected.append("completed")
        if not self._take_reached(stored.get("reached", FIRST_LEVEL)):
            rejected.append("reached")
        self._reconcile()
        return tuple(sorted(rejected))

    def _reconcile(self):
        """Make the two keys agree.

        A `reached` that is too high is clamped to the last level there is; one
        that is too low for the levels already finished was being accepted in
        silence, which offered a player who had beaten level three a CONTINUE
        that started them at level one.
        """
        if self.completed:
            self.reached = max(self.reached, self._unlocked_by(max(self.completed)))

    def _is_level(self, number):
        if isinstance(number, bool) or not isinstance(number, int):
            return False
        return number >= FIRST_LEVEL and (
            self.last_level is None or number <= self.last_level
        )

    def _take_completed(self, value):
        if not isinstance(value, list):
            return False
        kept = [number for number in value if self._is_level(number)]
        self.completed = tuple(sorted(set(kept)))
        # Counted against what was actually rejected, not against the
        # de-duplicated result: the same level twice is a repetitive file, not
        # a wrong one, and saying otherwise would name a key that was fine.
        return len(kept) == len(value)

    def _take_reached(self, value):
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        highest = self.last_level if self.last_level is not None else value
        # A file claiming level nine of a five level game is not a reason to
        # refuse to start; it is a reason to start at five.
        self.reached = max(FIRST_LEVEL, min(int(value), highest))
        return FIRST_LEVEL <= value <= highest

    def save(self):
        """Written beside the target and moved into place, so an interrupted
        save leaves the previous progress rather than half a file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(handle, "w") as opened:
                json.dump(
                    {"reached": self.reached, "completed": list(self.completed)},
                    opened,
                    indent=2,
                    sort_keys=True,
                )
            os.replace(temporary, self.path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
