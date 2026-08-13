"""Directional sprite runtime for the fixed-screen 2.5D demo.

Runtime artwork is intentionally file-convention driven so placeholder frames can
be replaced without touching Python.  Frames live at::

    Assets/Demo2_5D/actors/<kind>/<action>/<direction>/<frame>.png

For example ``actors/player/move/ne/00.png``.  Missing actions and directions
fall back to the demo's original static actor image; sprites are never rotated.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pygame


class Direction(str, Enum):
    """Eight screen-space compass directions."""

    E = "e"
    SE = "se"
    S = "s"
    SW = "sw"
    W = "w"
    NW = "nw"
    N = "n"
    NE = "ne"

    @classmethod
    def from_vector(
        cls, vector: pygame.Vector2, default: Direction | None = None
    ) -> Direction:
        """Return the closest 45-degree direction for a screen-space vector."""
        if vector.length_squared() == 0:
            return default or cls.S
        # Vector2.angle_to uses mathematical-positive angles while pygame's y
        # axis points downward.  The ordered sectors below follow screen space.
        angle = pygame.Vector2(1, 0).angle_to(vector) % 360
        index = int((angle + 22.5) // 45) % 8
        return (cls.E, cls.SE, cls.S, cls.SW, cls.W, cls.NW, cls.N, cls.NE)[index]


@dataclass(frozen=True)
class ActorGeometry:
    """Artwork-space attachment points measured from the image's top-left."""

    ground_anchor: tuple[float, float] = (0.5, 1.0)
    weapon_socket: tuple[float, float] | None = None

    def anchored_rect(
        self, image: pygame.Surface, ground_position: pygame.Vector2
    ) -> pygame.Rect:
        rect = image.get_rect()
        rect.x = round(ground_position.x - image.get_width() * self.ground_anchor[0])
        rect.y = round(ground_position.y - image.get_height() * self.ground_anchor[1])
        return rect

    def socket_position(
        self, image: pygame.Surface, ground_position: pygame.Vector2
    ) -> pygame.Vector2 | None:
        if self.weapon_socket is None:
            return None
        rect = self.anchored_rect(image, ground_position)
        return pygame.Vector2(
            rect.x + self.weapon_socket[0] * image.get_width(),
            rect.y + self.weapon_socket[1] * image.get_height(),
        )


@dataclass
class AnimationState:
    """Independent action, direction and frame clock for one actor."""

    action: str
    direction: Direction = Direction.S
    frame: int = 0
    frame_clock: float = 0.0
    finished: bool = False

    def set(self, action: str, direction: Direction) -> None:
        if action != self.action:
            self.action = action
            self.frame = 0
            self.frame_clock = 0.0
            self.finished = False
        self.direction = direction

    def advance(self, dt: float, frame_count: int, fps: float, *, loop: bool) -> None:
        if frame_count <= 1 or self.finished:
            return
        self.frame_clock += max(0.0, dt)
        frame_time = 1.0 / fps
        while self.frame_clock >= frame_time:
            self.frame_clock -= frame_time
            if self.frame + 1 < frame_count:
                self.frame += 1
            elif loop:
                self.frame = 0
            else:
                self.finished = True
                self.frame = frame_count - 1


class DirectionalSpriteSet:
    """Loads normalized directional PNG sequences with a static fallback."""

    def __init__(
        self,
        root: Path,
        kind: str,
        size: tuple[int, int],
        fallback: pygame.Surface,
        *,
        fps: dict[str, float] | None = None,
        geometry: ActorGeometry | None = None,
    ) -> None:
        self.root = root / "actors" / kind
        self.kind = kind
        self.size = size
        self.fallback = fallback
        self.fps = fps or {}
        self.geometry = geometry or ActorGeometry()
        self._frames: dict[tuple[str, Direction], tuple[pygame.Surface, ...]] = {}

    def frames(self, action: str, direction: Direction) -> tuple[pygame.Surface, ...]:
        key = (action, direction)
        if key not in self._frames:
            self._frames[key] = self._load_frames(action, direction)
        return self._frames[key]

    def preload(self, actions: tuple[str, ...]) -> None:
        """Read every runtime direction before the encounter begins."""
        for action in actions:
            for direction in Direction:
                self.frames(action, direction)

    def _load_frames(
        self, action: str, direction: Direction
    ) -> tuple[pygame.Surface, ...]:
        directory = self.root / action / direction.value
        paths = sorted(directory.glob("*.png")) if directory.is_dir() else []
        frames: list[pygame.Surface] = []
        for path in paths:
            try:
                image = pygame.image.load(path).convert_alpha()
                if image.get_size() != self.size:
                    image = pygame.transform.smoothscale(image, self.size)
                frames.append(image)
            except pygame.error:
                continue
        return tuple(frames) or (self.fallback,)

    def image(self, state: AnimationState) -> pygame.Surface:
        frames = self.frames(state.action, state.direction)
        return frames[min(state.frame, len(frames) - 1)]

    def update(self, state: AnimationState, dt: float, *, loop: bool = True) -> None:
        frames = self.frames(state.action, state.direction)
        state.advance(dt, len(frames), self.fps.get(state.action, 8.0), loop=loop)

    def draw(
        self,
        target: pygame.Surface,
        state: AnimationState,
        ground_position: pygame.Vector2,
    ) -> pygame.Rect:
        image = self.image(state)
        rect = self.geometry.anchored_rect(image, ground_position)
        target.blit(image, rect)
        return rect

    def weapon_socket(
        self, state: AnimationState, ground_position: pygame.Vector2
    ) -> pygame.Vector2 | None:
        return self.geometry.socket_position(self.image(state), ground_position)
