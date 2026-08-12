import json

import pygame
import pytest

from shooter import assets


def test_catalog_has_stable_gameplay_contracts():
    player = assets.get_asset("player.rifle.move")
    zombie = assets.get_asset("zombie.basic.move")

    assert player.kind == "animation"
    assert player.frame_count == 20
    assert player.fps == 60
    assert player.frame_paths()[0].endswith("survivor-move_rifle_0.png")
    assert zombie.collision_size == (120, 111)
    assert zombie.anchor == (0.5, 0.5)
    assert zombie.scaling == "smooth"


def test_catalog_references_existing_files():
    specs = assets.validate_catalog()

    assert len(specs) >= 20
    assert all(spec.frame_paths() for spec in specs)


def test_catalog_is_read_only_and_cached():
    first = assets.load_catalog()
    second = assets.load_catalog()

    assert first is second
    with pytest.raises(TypeError):
        first["new.asset"] = first["ui.cursor"]


def test_catalogued_image_uses_declared_size_and_cache():
    assets.load_asset.cache_clear()

    first = assets.load_asset("ui.cursor")
    second = assets.load_asset("ui.cursor")

    assert isinstance(first, pygame.Surface)
    assert first.get_size() == (46, 45)
    assert first is second
    assert assets.load_asset.cache_info().currsize == 1


def test_catalogued_animation_is_normalized_to_visual_size():
    frames = assets.load_asset("zombie.basic.idle")

    assert isinstance(frames, tuple)
    assert len(frames) == 17
    assert {frame.get_size() for frame in frames} == {(120, 111)}


def test_invalid_manifest_reports_asset_and_field(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "assets": {
                    "bad.anchor": {
                        "kind": "image",
                        "path": "cursor.png",
                        "frame_count": 1,
                        "fps": 0,
                        "visual_size": [46, 45],
                        "collision_size": None,
                        "anchor": [2, 0],
                        "scaling": "smooth",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"bad\.anchor: anchor"):
        assets.validate_catalog(manifest, check_files=False)
