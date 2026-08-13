from pathlib import Path

import pygame

from shooter.demos.actor_runtime import (
    ActorGeometry,
    AnimationState,
    Direction,
    DirectionalSpriteSet,
)


def test_direction_from_vector_covers_all_eight_screen_directions():
    vectors = (
        (pygame.Vector2(1, 0), Direction.E),
        (pygame.Vector2(1, 1), Direction.SE),
        (pygame.Vector2(0, 1), Direction.S),
        (pygame.Vector2(-1, 1), Direction.SW),
        (pygame.Vector2(-1, 0), Direction.W),
        (pygame.Vector2(-1, -1), Direction.NW),
        (pygame.Vector2(0, -1), Direction.N),
        (pygame.Vector2(1, -1), Direction.NE),
    )
    assert [Direction.from_vector(vector) for vector, _ in vectors] == [
        direction for _, direction in vectors
    ]


def test_zero_vector_preserves_supplied_direction():
    assert Direction.from_vector(pygame.Vector2(), Direction.NW) is Direction.NW


def test_animation_action_change_resets_frame_clock():
    state = AnimationState("idle", Direction.S, frame=3, frame_clock=0.4)
    state.set("move", Direction.N)
    assert (state.action, state.direction, state.frame, state.frame_clock) == (
        "move",
        Direction.N,
        0,
        0.0,
    )


def test_direction_change_does_not_reset_animation_clock():
    state = AnimationState("move", Direction.S, frame=2, frame_clock=0.04)
    state.set("move", Direction.N)
    assert (state.frame, state.frame_clock) == (2, 0.04)


def test_sprite_set_loads_predictable_sequence_and_falls_back(tmp_path: Path):
    fallback = pygame.Surface((16, 20), pygame.SRCALPHA)
    frame_dir = tmp_path / "actors" / "player" / "move" / "ne"
    frame_dir.mkdir(parents=True)
    for index, color in enumerate(((255, 0, 0), (0, 255, 0))):
        image = pygame.Surface((8, 10), pygame.SRCALPHA)
        image.fill(color)
        pygame.image.save(image, frame_dir / f"{index:02}.png")
    sprites = DirectionalSpriteSet(tmp_path, "player", (16, 20), fallback)
    assert len(sprites.frames("move", Direction.NE)) == 2
    assert sprites.frames("idle", Direction.S) == (fallback,)


def test_preload_warms_every_direction_for_each_action(tmp_path: Path):
    fallback = pygame.Surface((16, 20), pygame.SRCALPHA)
    sprites = DirectionalSpriteSet(tmp_path, "player", (16, 20), fallback)

    sprites.preload(("idle", "move"))

    assert len(sprites._frames) == 16


def test_geometry_uses_ground_anchor_and_weapon_socket():
    geometry = ActorGeometry((0.5, 0.75), (0.8, 0.25))
    image = pygame.Surface((100, 80))
    ground = pygame.Vector2(200, 300)
    assert geometry.anchored_rect(image, ground).topleft == (150, 240)
    assert geometry.socket_position(image, ground) == pygame.Vector2(230, 260)
