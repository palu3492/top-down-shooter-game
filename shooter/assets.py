"""Reading assets, once each.

`functools.cache` keys on the call as it was written, not on the arguments the
function ends up with -- so `load_image(path)` and `load_image(path, False)`
were two entries, two reads of the same file and two copies of the same surface.
Every loader here normalises its arguments before the cache sees them, so the
same file asked for two ways is the same surface.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cache
import json
from pathlib import Path
from types import MappingProxyType

import pygame

ASSETS_DIR = Path(__file__).resolve().parent.parent / "Assets"
MANIFEST_PATH = ASSETS_DIR / "manifest.json"
SCALING_MODES = frozenset(("nearest", "smooth"))


@dataclass(frozen=True)
class AssetSpec:
    """The rendering contract for one stable, named asset.

    Paths remain relative to :data:`ASSETS_DIR`.  Animations use ``directory``
    and ``prefix`` while still images use ``path``.  Sizes and anchors are
    metadata rather than pygame objects so the catalogue is safe to inspect in
    tools which have not initialised a display.
    """

    asset_id: str
    kind: str
    path: str | None
    directory: str | None
    prefix: str | None
    frame_count: int
    fps: float
    visual_size: tuple[int, int]
    collision_size: tuple[int, int] | None
    anchor: tuple[float, float]
    scaling: str

    def frame_paths(self) -> tuple[str, ...]:
        if self.kind == "image":
            return (self.path,) if self.path is not None else ()
        return tuple(
            f"{self.directory}/{self.prefix}{index}.png"
            for index in range(self.frame_count)
        )


def _pair(value, name, *, numeric_type):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name} must be a two-item array")
    if not all(isinstance(item, numeric_type) for item in value):
        raise ValueError(f"{name} has invalid values")
    return tuple(value)


def _parse_spec(asset_id, raw):
    kind = raw.get("kind")
    if kind not in ("image", "animation"):
        raise ValueError(f"{asset_id}: kind must be image or animation")
    path = raw.get("path")
    directory = raw.get("directory")
    prefix = raw.get("prefix")
    if kind == "image" and (not isinstance(path, str) or directory or prefix):
        raise ValueError(f"{asset_id}: an image needs only path")
    if kind == "animation" and (
        path or not isinstance(directory, str) or not isinstance(prefix, str)
    ):
        raise ValueError(f"{asset_id}: an animation needs directory and prefix")

    frame_count = raw.get("frame_count")
    fps = raw.get("fps")
    if not isinstance(frame_count, int) or frame_count < 1:
        raise ValueError(f"{asset_id}: frame_count must be positive")
    if not isinstance(fps, (int, float)) or fps < 0:
        raise ValueError(f"{asset_id}: fps must be non-negative")
    if kind == "image" and (frame_count != 1 or fps != 0):
        raise ValueError(f"{asset_id}: images use frame_count 1 and fps 0")

    visual_size = _pair(
        raw.get("visual_size"), f"{asset_id}: visual_size", numeric_type=int
    )
    if any(value < 1 for value in visual_size):
        raise ValueError(f"{asset_id}: visual_size must be positive")
    collision = raw.get("collision_size")
    collision_size = None
    if collision is not None:
        collision_size = _pair(
            collision, f"{asset_id}: collision_size", numeric_type=int
        )
        if any(value < 1 for value in collision_size):
            raise ValueError(f"{asset_id}: collision_size must be positive")
    anchor = _pair(raw.get("anchor"), f"{asset_id}: anchor", numeric_type=(int, float))
    if any(value < 0 or value > 1 for value in anchor):
        raise ValueError(f"{asset_id}: anchor must be normalized")
    scaling = raw.get("scaling")
    if scaling not in SCALING_MODES:
        raise ValueError(f"{asset_id}: unknown scaling mode {scaling!r}")
    return AssetSpec(
        asset_id, kind, path, directory, prefix, frame_count, float(fps),
        visual_size, collision_size, anchor, scaling,
    )


@cache
def load_catalog(path=MANIFEST_PATH) -> Mapping[str, AssetSpec]:
    """Read and validate the asset catalogue once."""
    path = Path(path)
    with path.open(encoding="utf-8") as manifest:
        document = json.load(manifest)
    if document.get("version") != 1 or not isinstance(document.get("assets"), dict):
        raise ValueError("asset manifest must contain version 1 and an assets object")
    specs = {
        asset_id: _parse_spec(asset_id, raw)
        for asset_id, raw in document["assets"].items()
    }
    return MappingProxyType(specs)


def get_asset(asset_id: str) -> AssetSpec:
    """Return metadata for a stable asset ID, raising ``KeyError`` if unknown."""
    return load_catalog()[asset_id]


def iter_assets() -> Iterator[AssetSpec]:
    return iter(load_catalog().values())


def validate_catalog(path=MANIFEST_PATH, *, check_files=True) -> tuple[AssetSpec, ...]:
    """Validate schema and, by default, that every referenced file exists."""
    specs = tuple(load_catalog(Path(path)).values())
    if check_files:
        missing = [
            relative
            for spec in specs
            for relative in spec.frame_paths()
            if not (ASSETS_DIR / relative).is_file()
        ]
        if missing:
            raise FileNotFoundError("missing catalogued assets: " + ", ".join(missing))
    return specs


def _resize(image, size, scaling):
    transform = (
        pygame.transform.smoothscale
        if scaling == "smooth"
        else pygame.transform.scale
    )
    return transform(image, size)


@cache
def _catalog_asset(asset_id):
    spec = get_asset(asset_id)
    alpha = all(
        Path(relative).suffix.lower() == ".png" for relative in spec.frame_paths()
    )
    frames = tuple(
        _resize(_image(relative, alpha), spec.visual_size, spec.scaling)
        for relative in spec.frame_paths()
    )
    return frames[0] if spec.kind == "image" else frames


def load_asset(asset_id):
    """Load a catalogued asset at its declared visual size.

    Images return a Surface and animations return an immutable frame tuple.
    Existing path-based loaders remain available during incremental migration.
    """
    return _catalog_asset(asset_id)


def asset_path(relative):
    return str(ASSETS_DIR / relative)


def _cache_controls(public, cached):
    """Keep `cache_info` and `cache_clear` reachable through the public name."""
    public.cache_info = cached.cache_info
    public.cache_clear = cached.cache_clear
    return public


@cache
def _image(relative, alpha):
    image = pygame.image.load(asset_path(relative))
    return image.convert_alpha() if alpha else image


def load_image(relative, alpha=False):
    return _image(relative, bool(alpha))


@cache
def _scaled(relative, factor, alpha):
    image = _image(relative, alpha)
    size = (int(image.get_width() * factor), int(image.get_height() * factor))
    return pygame.transform.scale(image, size)


def load_scaled(relative, factor, alpha=False):
    return _scaled(relative, factor, bool(alpha))


@cache
def _sized(relative, width, height, alpha):
    return pygame.transform.scale(_image(relative, alpha), (width, height))


def load_sized(relative, width, height, alpha=False):
    return _sized(relative, width, height, bool(alpha))


@cache
def _sheet(relative):
    return pygame.image.load(asset_path(relative)).convert()


def load_sheet(relative):
    """A large image sampled from rather than blitted whole.

    Cached like everything else: the world background is 5000x5000 and costs
    180ms to read and convert, which should be paid once for the process rather
    than once per game.
    """
    return _sheet(relative)


@cache
def _sound(relative):
    return pygame.mixer.Sound(asset_path(relative))


def load_sound(relative):
    return _sound(relative)


@cache
def _animation(directory, prefix, count, factor, alpha):
    return tuple(
        load_scaled(f"{directory}/{prefix}{i}.png", factor, alpha) for i in range(count)
    )


def load_animation(directory, prefix, count, factor, alpha=False):
    return _animation(directory, prefix, count, factor, bool(alpha))


for _public, _cached in (
    (load_asset, _catalog_asset),
    (load_image, _image),
    (load_scaled, _scaled),
    (load_sized, _sized),
    (load_sheet, _sheet),
    (load_sound, _sound),
    (load_animation, _animation),
):
    _cache_controls(_public, _cached)
