# TMX Semantic Schema (draft v2)

This document defines gameplay data authored in Tiled. Layer names, layer order,
capitalization, and visible artwork are organizational choices; they do not decide
gameplay behavior.

## Map metadata

Every production map has these map properties:

| Property | Type | Required | Meaning |
|---|---|---:|---|
| `schema_version` | integer | yes | Semantic schema version, currently `2`. |
| `map_id` | string | yes | Stable map identifier. |
| `display_name` | string | yes | Player-facing name. |
| `supported_modes` | string | no | Comma-separated mode identifiers. |

## Semantic object contract

Every gameplay-relevant object has a custom string property named `semantic`.
Its name is the preferred stable semantic ID; unnamed geometry falls back to its
stable TMX object ID. IDs must be unique within a semantic type. Harvestable
instances always use their TMX object ID because their display names may repeat.
Objects may live on any object layer.

| `semantic` value | Required data | Optional data |
|---|---|---|
| `static_blocker` | A rectangle, ellipse, polygon, or polyline | `clearance` (polyline width, defaults from its reusable Tiled type) |
| `playable_area` | A closed rectangle, ellipse, or polygon | — |
| `spawn` | `role` | `tags`, `faction`, `actor_kind`, `weight` |
| `interaction` | `kind` | Mode-specific offer properties such as `weapon_id` and `price` |
| `harvestable` | `kind`, `durability`, `resource_id`, `resource_yield`, `required_tool_capability` | `collision_source` |
| `construction_anchor` | `kind` | Recipe and durability properties |

The adapter must reject unknown semantic values, duplicate IDs, missing required
properties, invalid numbers, empty geometry, and invalid collision sources with
the map path, layer name, object ID, and object name in its error.

Maps marked `schema_version = 2` are validated against this contract. Version 1
maps are no longer accepted; migrate their objects to explicit semantic
properties before loading them.

## Reusable Tiled templates

The current map project includes reusable templates under
`Assets/Maps/world_1/templates/`: `SolidProp`, `Fence`, `Building`,
`Harvestable`, and `ConstructionAnchor`. Instantiate the closest template before
placing a gameplay object. `Harvestable` deliberately starts invalid until its
kind, resource, and durability values are authored; this prevents silently
shipping a generic prop with accidental gameplay behavior.

Trees and vehicles use `collision_source = tile`. Their collision polygons live
on their individual tiles in the tileset, so every placement inherits the same
footprint at its placed scale. Do not add `source_*` polygon properties to map
instances; those were transitional migration data and have been removed.

## Reusable Tiled types

Create these as Tiled custom object types or templates. Their default properties
are authoring defaults, not Python fallback behavior.

| Tiled type/template | Semantic | Key defaults |
|---|---|---|
| `SolidProp` | `static_blocker` | Collision geometry authored on object. |
| `Fence` | `static_blocker` | Polyline plus authored `clearance`. |
| `Building` | `static_blocker` | Polygon/rectangle footprint. |
| `HarvestableTree` | `harvestable` | Wood, durability, yield, harvest capability, `collision_source=tile`. |
| `HarvestableVehicle` | `harvestable` | Metal, durability, yield, harvest capability, `collision_source=tile`. |
| `ConstructionAnchor` | `construction_anchor` | Barricade recipe/properties. |

`Placed Trees` and vehicles may remain visual layers, but each placed object
must carry the appropriate semantic data or inherit it from its Tiled template.
Their visible image bounds are never assumed to be collision footprints. A
`collision_source=tile` object receives only its selected tile's collision
shapes, scaled to its placed size.

## Migration rules

1. New maps use this schema immediately.
2. The adapter temporarily accepts the current named layers as legacy aliases.
3. Migrate each production object to `semantic` data, retaining its current
   stable name and visual placement.
4. Add tile collision shapes to each reusable vehicle tile before enabling
   vehicle blocking.
5. Remove legacy aliases and Python-authored prop defaults only after the
   production map and fixtures pass schema validation.
