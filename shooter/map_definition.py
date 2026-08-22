"""Neutral map data and the Tiled adapter that produces it."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from xml.etree import ElementTree

from shooter.assets import asset_path
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


@cache
def load_tmx_definition(source, presentation_source=None):
    """Adapt available TMX semantics without requiring a complete future schema."""
    given = Path(source)
    path = given if given.exists() else Path(asset_path(source))
    root = ElementTree.parse(path).getroot()
    metadata = _properties(root)
    collisions = []
    for layer in root.findall("objectgroup"):
        layer_name = layer.get("name", "")
        include = layer_name in {"Collision", "Obstacles"}
        offset_x = float(layer.get("offsetx", 0))
        offset_y = float(layer.get("offsety", 0))
        for obj in layer.findall("object"):
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
    )


def current_map_definition():
    return load_tmx_definition(CURRENT_MAP_SOURCE)
