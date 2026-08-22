"""The deliberately small, pygame-free contract hosted by Match."""

from typing import Protocol


class GameMode(Protocol):
    """One fresh rules instance for one Match lifecycle."""

    def start(self, match) -> None: ...

    def advance(self, match, commands: tuple, dt: float) -> None: ...

    def status(self, match): ...

    def result(self, match): ...

    def dispose(self, match) -> None: ...
