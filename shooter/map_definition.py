"""Neutral map data and the Tiled adapter that produces it."""

from dataclasses import dataclass
from functools import cache
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree

from shooter.asset_paths import asset_path
from shooter.world_collision import Aabb, Ellipse, Polygon

CURRENT_MAP_SOURCE = "Maps/world_1/world_1.tmx"
FENCE_COLLISION_WIDTH = 32.0


class TmxSchemaError(ValueError):
    """An authored semantic object is incomplete or invalid."""

    def __init__(self, path, layer, obj, message):
        super().__init__(
            f"{path}: layer '{layer}', object {obj.get('id', '?')} "
            f"('{obj.get('name', '')}'): {message}"
        )


class TmxMapSchemaError(ValueError):
    """Map-level TMX schema metadata is incomplete or unsupported."""

    def __init__(self, path, message):
        super().__init__(f"{path}: map metadata: {message}")


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
    harvestables: tuple["MapHarvestable", ...] = ()
    construction_anchors: tuple["MapConstructionAnchor", ...] = ()
    playable_areas: tuple[Aabb | Ellipse | Polygon, ...] = ()

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
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class SpawnRegion:
    spawn_id: str
    area: Aabb | Ellipse | Polygon
    role: str = ""
    tags: frozenset[str] = frozenset()
    faction: str | None = None
    actor_kind: str | None = None
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class MapInteraction:
    interaction_id: str
    kind: str
    position: tuple[float, float] | None = None
    area: Aabb | Ellipse | Polygon | None = None
    tags: frozenset[str] = frozenset()
    properties: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MapHarvestable:
    harvestable_id: str
    kind: str
    position: tuple[float, float] | None = None
    area: Aabb | Ellipse | Polygon | None = None
    tags: frozenset[str] = frozenset()
    properties: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MapConstructionAnchor:
    anchor_id: str
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


def _validate_schema_metadata(path, metadata):
    """Validate schema-v2 metadata while preserving legacy fixture maps."""
    version = metadata.get("schema_version")
    if version is None:
        return
    if version == "1":
        return
    if version != "2":
        raise TmxMapSchemaError(path, f"unsupported schema_version '{version}'")
    missing = tuple(
        name for name in ("map_id", "display_name") if not metadata.get(name)
    )
    if missing:
        raise TmxMapSchemaError(path, f"missing properties: {', '.join(missing)}")


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
        return Ellipse(x, y, width, height) if width > 0 and height > 0 else None
    if width > 0 and height > 0:
        return Aabb(x, y, width, height)
    return None


def _tile_collision_catalog(root):
    """Return image dimensions and collision objects keyed by global tile ID."""
    catalog = {}
    for tileset in root.findall("tileset"):
        first_gid = int(tileset.get("firstgid", 1))
        for tile in tileset.findall("tile"):
            collision_group = tile.find("objectgroup")
            if collision_group is None:
                continue
            image = tile.find("image")
            if image is None:
                continue
            image_width = float(image.get("width", 0))
            image_height = float(image.get("height", 0))
            if image_width <= 0 or image_height <= 0:
                continue
            catalog[first_gid + int(tile.get("id", 0))] = (
                image_width,
                image_height,
                tuple(collision_group.findall("object")),
            )
    return catalog


def _tile_collision_shapes(obj, offset_x, offset_y, catalog):
    """Scale a tile's authored shapes to one object-layer tile instance."""
    definition = catalog.get(int(obj.get("gid", 0)))
    if definition is None:
        return ()
    image_width, image_height, collision_objects = definition
    scale_x = float(obj.get("width", image_width)) / image_width
    scale_y = float(obj.get("height", image_height)) / image_height
    origin_x = float(obj.get("x", 0)) + offset_x
    origin_y = float(obj.get("y", 0)) + offset_y
    shapes = []
    for collision_obj in collision_objects:
        local_x = float(collision_obj.get("x", 0))
        local_y = float(collision_obj.get("y", 0))
        polygon = collision_obj.find("polygon")
        if polygon is not None:
            points = tuple(
                (
                    origin_x + (local_x + float(pair.split(",")[0])) * scale_x,
                    origin_y + (local_y + float(pair.split(",")[1])) * scale_y,
                )
                for pair in polygon.get("points", "").split()
            )
            if len(points) >= 3:
                shapes.append(Polygon(points))
            continue
        width = float(collision_obj.get("width", 0)) * scale_x
        height = float(collision_obj.get("height", 0)) * scale_y
        x = origin_x + local_x * scale_x
        y = origin_y + local_y * scale_y
        if collision_obj.find("ellipse") is not None:
            shapes.append(Ellipse(x, y, width, height))
        elif width > 0 and height > 0:
            shapes.append(Aabb(x, y, width, height))
    return tuple(shapes)


def _polyline_shapes(obj, offset_x, offset_y, width=FENCE_COLLISION_WIDTH):
    polyline = obj.find("polyline")
    if polyline is None:
        return ()
    origin_x = float(obj.get("x", 0)) + offset_x
    origin_y = float(obj.get("y", 0)) + offset_y
    points = tuple(
        (
            origin_x + float(pair.split(",")[0]),
            origin_y + float(pair.split(",")[1]),
        )
        for pair in polyline.get("points", "").split()
    )
    half_width = width / 2
    shapes = []
    for start, end in pairwise(points):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            continue
        offset = (-dy / length * half_width, dx / length * half_width)
        shapes.append(
            Polygon(
                (
                    (start[0] + offset[0], start[1] + offset[1]),
                    (end[0] + offset[0], end[1] + offset[1]),
                    (end[0] - offset[0], end[1] - offset[1]),
                    (start[0] - offset[0], start[1] - offset[1]),
                )
            )
        )
    return tuple(shapes)


def _is_point(obj):
    return obj.get("point") == "1" or (
        float(obj.get("width", 0)) == 0 and float(obj.get("height", 0)) == 0
    )


def _csv(value):
    return frozenset(part.strip() for part in value.split(",") if part.strip())


def _spawn(obj, offset_x, offset_y, properties=None):
    properties = _properties(obj) if properties is None else properties
    common = {
        "spawn_id": obj.get("name") or f"spawn-{obj.get('id', 'unknown')}",
        "role": properties.get("role", ""),
        "tags": _csv(properties.get("tags", "")),
        "faction": properties.get("faction") or None,
        "actor_kind": properties.get("actor_kind") or None,
        "weight": max(0.0, float(properties.get("weight", 1))),
    }
    x = float(obj.get("x", 0)) + offset_x
    y = float(obj.get("y", 0)) + offset_y
    if _is_point(obj):
        return SpawnPoint(position=(x, y), **common)
    area = _shape(obj, offset_x, offset_y)
    return None if area is None else SpawnRegion(area=area, **common)


def _interaction(obj, offset_x, offset_y, properties=None):
    properties = _properties(obj) if properties is None else properties
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
    if _is_point(obj):
        return MapInteraction(position=(x, y), **common)
    area = _shape(obj, offset_x, offset_y)
    return None if area is None else MapInteraction(area=area, **common)


def _harvestable(obj, offset_x, offset_y, properties=None):
    properties = _properties(obj) if properties is None else properties
    kind = properties.get("kind") or obj.get("type", "")
    if not kind or kind == "harvestable":
        return None
    common = {
        "harvestable_id": obj.get("name") or f"harvestable-{obj.get('id', 'unknown')}",
        "kind": kind,
        "tags": _csv(properties.get("tags", "")),
        "properties": tuple(sorted(properties.items())),
    }
    x = float(obj.get("x", 0)) + offset_x
    y = float(obj.get("y", 0)) + offset_y
    if _is_point(obj):
        return MapHarvestable(position=(x, y), **common)
    area = _shape(obj, offset_x, offset_y)
    return None if area is None else MapHarvestable(area=area, **common)


def _environment_harvestable(obj, offset_x, offset_y, layer_name):
    """Adapt visible TMX prop layers without duplicating their artwork in code."""
    kind = obj.get("type", "").lower()
    if kind not in {"tree", "vehicle"}:
        return None
    area = _shape(obj, offset_x, offset_y)
    if area is None:
        return None
    defaults = (
        ("durability", "150" if kind == "tree" else "200"),
        ("resource_id", "wood" if kind == "tree" else "metal"),
        ("resource_yield", "12" if kind == "tree" else "8"),
        ("debug_render", "false"),
    )
    values = (*tuple(sorted(_properties(obj).items())), *defaults)
    identifier = layer_name.lower().replace(" ", "-")
    return MapHarvestable(
        f"{identifier}-{obj.get('id', 'unknown')}",
        kind,
        area=area,
        tags=frozenset(("environment",)),
        properties=values,
    )


def _authored_semantic(path, layer_name, obj, offset_x, offset_y, defaults=()):
    """Adapt one schema-v2 object without depending on its presentation layer."""
    properties = {**dict(defaults), **_properties(obj)}
    semantic = properties.get("semantic")
    if semantic is None:
        return None
    if semantic == "static_blocker":
        shape = _shape(obj, offset_x, offset_y)
        if shape is not None:
            return semantic, (shape,)
        clearance = properties.get("clearance")
        if clearance is None:
            raise TmxSchemaError(
                path, layer_name, obj, "requires geometry or clearance"
            )
        try:
            width = float(clearance)
        except ValueError as error:
            raise TmxSchemaError(
                path, layer_name, obj, "clearance must be numeric"
            ) from error
        shapes = _polyline_shapes(obj, offset_x, offset_y, width)
        if width <= 0 or not shapes:
            raise TmxSchemaError(
                path,
                layer_name,
                obj,
                "requires a non-empty positive-width polyline",
            )
        return semantic, shapes
    if semantic == "playable_area":
        shape = _shape(obj, offset_x, offset_y)
        if shape is None:
            raise TmxSchemaError(path, layer_name, obj, "requires closed area geometry")
        return semantic, (shape,)
    if semantic == "spawn":
        if not properties.get("role"):
            raise TmxSchemaError(path, layer_name, obj, "requires a role")
        value = _spawn(obj, offset_x, offset_y, properties)
        if value is None:
            raise TmxSchemaError(
                path, layer_name, obj, "requires point or area geometry"
            )
        return semantic, (value,)
    if semantic == "interaction":
        if not properties.get("kind"):
            raise TmxSchemaError(path, layer_name, obj, "requires a kind")
        value = _interaction(obj, offset_x, offset_y, properties)
        if value is None:
            raise TmxSchemaError(
                path, layer_name, obj, "requires point or area geometry"
            )
        return semantic, (value,)
    if semantic == "harvestable":
        required = (
            "kind",
            "durability",
            "resource_id",
            "resource_yield",
            "required_tool_capability",
        )
        missing = tuple(name for name in required if not properties.get(name))
        if missing:
            raise TmxSchemaError(
                path, layer_name, obj, f"missing properties: {', '.join(missing)}"
            )
        for property_name in ("durability", "resource_yield"):
            try:
                value = float(properties[property_name])
            except ValueError as error:
                raise TmxSchemaError(
                    path, layer_name, obj, f"{property_name} must be numeric"
                ) from error
            if value < 0 or (property_name == "durability" and value == 0):
                raise TmxSchemaError(
                    path, layer_name, obj, f"{property_name} must be positive"
                )
        value = _harvestable(obj, offset_x, offset_y, properties)
        if value is None:
            raise TmxSchemaError(path, layer_name, obj, "requires area geometry")
        return semantic, (value,)
    if semantic == "construction_anchor":
        if not properties.get("kind"):
            raise TmxSchemaError(path, layer_name, obj, "requires a kind")
        value = _construction_anchor(obj, offset_x, offset_y, properties)
        if value is None:
            raise TmxSchemaError(
                path, layer_name, obj, "requires point or area geometry"
            )
        return semantic, (value,)
    raise TmxSchemaError(path, layer_name, obj, f"unknown semantic '{semantic}'")


def _construction_anchor(obj, offset_x, offset_y, properties=None):
    properties = _properties(obj) if properties is None else properties
    kind = properties.get("kind") or obj.get("type", "") or "barricade"
    common = {
        "anchor_id": obj.get("name") or f"anchor-{obj.get('id', 'unknown')}",
        "kind": kind,
        "tags": _csv(properties.get("tags", "")),
        "properties": tuple(sorted(properties.items())),
    }
    x = float(obj.get("x", 0)) + offset_x
    y = float(obj.get("y", 0)) + offset_y
    if _is_point(obj):
        return MapConstructionAnchor(position=(x, y), **common)
    area = _shape(obj, offset_x, offset_y)
    return None if area is None else MapConstructionAnchor(area=area, **common)


@cache
def load_tmx_definition(source, presentation_source=None):
    """Adapt available TMX semantics without requiring a complete future schema."""
    given = Path(source)
    path = given if given.exists() else Path(asset_path(source))
    root = ElementTree.parse(path).getroot()
    tile_collision_catalog = _tile_collision_catalog(root)
    metadata = _properties(root)
    _validate_schema_metadata(path, metadata)
    collisions = []
    spawns = []
    interactions = []
    harvestables = []
    construction_anchors = []
    playable_areas = []
    semantic_ids = set()
    for layer in root.findall("objectgroup"):
        layer_name = layer.get("name", "")
        layer_properties = _properties(layer)
        include = layer_name in {"Collision", "Obstacles"}
        offset_x = float(layer.get("offsetx", 0))
        offset_y = float(layer.get("offsety", 0))
        for obj in layer.findall("object"):
            authored = _authored_semantic(
                path, layer_name, obj, offset_x, offset_y, layer_properties.items()
            )
            if authored is not None:
                semantic, values = authored
                name = obj.get("name", "")
                object_id = obj.get("id", "")
                if not name and not object_id:
                    raise TmxSchemaError(
                        path, layer_name, obj, "requires a stable name or object ID"
                    )
                # Harvestable instances are commonly cloned from a small set of
                # named Tiled tiles.  Their TMX object id, rather than the
                # repeated display name, is therefore their stable identity.
                identity = semantic, (
                    object_id if semantic == "harvestable" else name or object_id
                )
                if identity in semantic_ids:
                    raise TmxSchemaError(
                        path, layer_name, obj, f"duplicate {semantic} name '{name}'"
                    )
                semantic_ids.add(identity)
                if semantic == "static_blocker":
                    collisions.extend(values)
                elif semantic == "playable_area":
                    playable_areas.extend(values)
                elif semantic == "spawn":
                    spawns.extend(values)
                elif semantic == "interaction":
                    interactions.extend(values)
                elif semantic == "harvestable":
                    harvestables.extend(values)
                    object_properties = {**layer_properties, **_properties(obj)}
                    collision_source = object_properties.get("collision_source")
                    if collision_source == "tile":
                        shapes = _tile_collision_shapes(
                            obj, offset_x, offset_y, tile_collision_catalog
                        )
                        if not shapes:
                            raise TmxSchemaError(
                                path,
                                layer_name,
                                obj,
                                "collision_source=tile requires tile collision "
                                "geometry",
                            )
                        collisions.extend(shapes)
                    elif collision_source not in {None, "none"}:
                        raise TmxSchemaError(
                            path,
                            layer_name,
                            obj,
                            f"unknown collision_source '{collision_source}'",
                        )
                else:
                    construction_anchors.extend(values)
                continue
            if layer_name in {"Placed Trees", "Trees", "vehicles", "Vehicles"}:
                harvestable = _environment_harvestable(
                    obj, offset_x, offset_y, layer_name
                )
                if harvestable is not None:
                    harvestables.append(harvestable)
                if layer_name in {"Placed Trees", "Trees"}:
                    collisions.extend(
                        _tile_collision_shapes(
                            obj, offset_x, offset_y, tile_collision_catalog
                        )
                    )
                continue
            if layer_name == "Buildings":
                shape = _shape(obj, offset_x, offset_y)
                if shape is not None:
                    collisions.append(shape)
                continue
            if layer_name in {"Tree Colliders", "Vehicle Colliders"}:
                shape = _shape(obj, offset_x, offset_y)
                if shape is not None:
                    collisions.append(shape)
                continue
            if layer_name == "Fence":
                collisions.extend(_polyline_shapes(obj, offset_x, offset_y))
                continue
            if layer_name == "Playable Area":
                shape = _shape(obj, offset_x, offset_y)
                if shape is not None:
                    playable_areas.append(shape)
                continue
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
            if layer_name == "Harvestables":
                harvestable = _harvestable(obj, offset_x, offset_y)
                if harvestable is not None:
                    harvestables.append(harvestable)
                continue
            if layer_name == "ConstructionAnchors":
                anchor = _construction_anchor(obj, offset_x, offset_y)
                if anchor is not None:
                    construction_anchors.append(anchor)
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
    if harvestables:
        capabilities.add("harvestables")
        capabilities.update(
            f"harvestable:{harvestable.kind}" for harvestable in harvestables
        )
    if construction_anchors:
        capabilities.add("construction_anchors")
        capabilities.update(
            f"construction_anchor:{anchor.kind}" for anchor in construction_anchors
        )
    if playable_areas:
        capabilities.add("playable_area")
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
        harvestables=tuple(harvestables),
        construction_anchors=tuple(construction_anchors),
        playable_areas=tuple(playable_areas),
    )


def current_map_definition():
    return load_tmx_definition(CURRENT_MAP_SOURCE)
