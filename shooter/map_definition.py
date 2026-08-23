"""Neutral map data and the Tiled adapter that produces it."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from xml.etree import ElementTree

from shooter.asset_paths import asset_path
from shooter.world_collision import Aabb, Ellipse, Polygon

CURRENT_MAP_SOURCE = "Maps/world_1/world_1.tmx"


@dataclass(frozen=True, slots=True)
class MapDefinition:
    map_id: str
    display_name: str
    presentation_source: str
    size: tuple[int, int]
    collision: tuple[Aabb | Ellipse | Polygon, ...] = ()
    capabilities: frozenset[str] = frozenset()
    spawns: tuple["SpawnPoint | SpawnRegion", ...] = ()
    supported_modes: frozenset[str] = frozenset()
    interactions: tuple["MapInteraction", ...] = ()

    def spawn_roles(self):
        return frozenset(spawn.role for spawn in self.spawns if spawn.role)

    def validate(self, requirements: "MapRequirements"):
        missing_capabilities = requirements.capabilities - self.capabilities
        missing_spawn_roles = requirements.spawn_roles - self.spawn_roles()
        return MapCapabilityReport(missing_capabilities, missing_spawn_roles)


@dataclass(frozen=True, slots=True)
class SpawnPoint:
    spawn_id: str
    position: tuple[float, float]
    role: str = ""
    tags: frozenset[str] = frozenset()
    faction: str | None = None
    actor_kind: str | None = None


@dataclass(frozen=True, slots=True)
class SpawnRegion:
    spawn_id: str
    area: Aabb | Ellipse | Polygon
    role: str = ""
    tags: frozenset[str] = frozenset()
    faction: str | None = None
    actor_kind: str | None = None


@dataclass(frozen=True, slots=True)
class MapInteraction:
    interaction_id: str
    kind: str
    position: tuple[float, float] | None = None
    area: Aabb | Ellipse | Polygon | None = None
    tags: frozenset[str] = frozenset()
    properties: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MapRequirements:
    capabilities: frozenset[str] = frozenset()
    spawn_roles: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class MapCapabilityReport:
    missing_capabilities: frozenset[str] = frozenset()
    missing_spawn_roles: frozenset[str] = frozenset()

    @property
    def compatible(self):
        return not self.missing_capabilities and not self.missing_spawn_roles


def _properties(element):
    properties = element.find("properties")
    if properties is None:
        return {}
    return {
        item.get("name"): item.get("value", item.text or "")
        for item in properties.findall("property")
    }


def _shape(obj, offset_x, offset_y):
    x = float(obj.get("x", 0)) + offset_x
    y = float(obj.get("y", 0)) + offset_y
    width = float(obj.get("width", 0))
    height = float(obj.get("height", 0))
    polygon = obj.find("polygon")
    if polygon is not None:
        points = tuple(
            (x + float(pair.split(",")[0]), y + float(pair.split(",")[1]))
            for pair in polygon.get("points", "").split()
        )
        return Polygon(points) if len(points) >= 3 else None
    if obj.find("ellipse") is not None:
        return Ellipse(x, y, width, height)
    if width > 0 and height > 0:
        return Aabb(x, y, width, height)
    return None


def _csv(value):
    return frozenset(part.strip() for part in value.split(",") if part.strip())


def _spawn(obj, offset_x, offset_y):
    properties = _properties(obj)
    common = {
        "spawn_id": obj.get("name") or f"spawn-{obj.get('id', 'unknown')}",
        "role": properties.get("role", ""),
        "tags": _csv(properties.get("tags", "")),
        "faction": properties.get("faction") or None,
        "actor_kind": properties.get("actor_kind") or None,
    }
    x = float(obj.get("x", 0)) + offset_x
    y = float(obj.get("y", 0)) + offset_y
    if obj.get("point") == "1":
        return SpawnPoint(position=(x, y), **common)
    area = _shape(obj, offset_x, offset_y)
    return None if area is None else SpawnRegion(area=area, **common)


def _interaction(obj, offset_x, offset_y):
    properties = _properties(obj)
    kind = properties.get("kind") or obj.get("type", "")
    if not kind or kind == "interaction":
        return None
    common = {
        "interaction_id": obj.get("name") or f"interaction-{obj.get('id', 'unknown')}",
        "kind": kind,
        "tags": _csv(properties.get("tags", "")),
        "properties": tuple(sorted(properties.items())),
    }
    x = float(obj.get("x", 0)) + offset_x
    y = float(obj.get("y", 0)) + offset_y
    if obj.get("point") == "1":
        return MapInteraction(position=(x, y), **common)
    area = _shape(obj, offset_x, offset_y)
    return None if area is None else MapInteraction(area=area, **common)


@cache
def load_tmx_definition(source, presentation_source=None):
    """Adapt available TMX semantics without requiring a complete future schema."""
    given = Path(source)
    path = given if given.exists() else Path(asset_path(source))
    root = ElementTree.parse(path).getroot()
    metadata = _properties(root)
    collisions = []
    spawns = []
    interactions = []
    for layer in root.findall("objectgroup"):
        layer_name = layer.get("name", "")
        include = layer_name in {"Collision", "Obstacles"}
        offset_x = float(layer.get("offsetx", 0))
        offset_y = float(layer.get("offsety", 0))
        for obj in layer.findall("object"):
            if layer_name == "Spawns":
                spawn = _spawn(obj, offset_x, offset_y)
                if spawn is not None:
                    spawns.append(spawn)
                continue
            if layer_name == "Interactions":
                interaction = _interaction(obj, offset_x, offset_y)
                if interaction is not None:
                    interactions.append(interaction)
                continue
            solid = _properties(obj).get("solid", "false").lower() == "true"
            if not include and not solid:
                continue
            shape = _shape(obj, offset_x, offset_y)
            if shape is not None:
                collisions.append(shape)

    map_id = metadata.get("map_id", path.stem)
    capabilities = {"bounds"}
    if collisions:
        capabilities.add("collision")
    if spawns:
        capabilities.add("spawns")
    if interactions:
        capabilities.add("interactions")
        capabilities.update(
            f"interaction:{interaction.kind}" for interaction in interactions
        )
    return MapDefinition(
        map_id=map_id,
        display_name=metadata.get("display_name", map_id.replace("_", " ").title()),
        presentation_source=presentation_source or str(source),
        size=(
            int(root.get("width", 0)) * int(root.get("tilewidth", 0)),
            int(root.get("height", 0)) * int(root.get("tileheight", 0)),
        ),
        collision=tuple(collisions),
        capabilities=frozenset(capabilities),
        spawns=tuple(spawns),
        supported_modes=_csv(metadata.get("supported_modes", "")),
        interactions=tuple(interactions),
    )


def current_map_definition():
    return load_tmx_definition(CURRENT_MAP_SOURCE)
