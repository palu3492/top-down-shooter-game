"""Production-neutral map definitions from incomplete Tiled maps."""

from pathlib import Path

import pytest

from shooter.map_definition import (
    MapDefinition,
    MapHarvestable,
    MapInteraction,
    MapRequirements,
    SpawnPoint,
    SpawnRegion,
    current_map_definition,
    load_tmx_definition,
    TmxMapSchemaError,
    TmxSchemaError,
)
from shooter.session import Session
from shooter.viewport import Viewport
from shooter.world_collision import Aabb, Polygon

WINDOW = (1080, 720)
FIXTURES = Path(__file__).parent / "fixtures" / "maps"
CURRENT_PRESENTATION = "Maps/world_1/world_1.tmx"


def test_incomplete_tmx_maps_adapt_without_requiring_future_layers():
    crossroads = load_tmx_definition(FIXTURES / "crossroads.tmx")
    riverside = load_tmx_definition(FIXTURES / "riverside.tmx")

    assert crossroads.map_id == "crossroads"
    assert riverside.map_id == "riverside"
    assert crossroads.size != riverside.size
    assert riverside.capabilities == {
        "bounds",
        "collision",
        "spawns",
    }
    assert crossroads.capabilities == {
        "bounds",
        "collision",
        "spawns",
        "interactions",
        "interaction:weapon_station",
    }
    assert crossroads.collision != riverside.collision
    assert crossroads.spawn_roles() >= {"survivor", "enemy", "team_a", "team_b"}
    assert riverside.spawn_roles() == {"survivor", "enemy"}
    assert "team_deathmatch" in crossroads.supported_modes
    assert "team_deathmatch" not in riverside.supported_modes
    assert crossroads.interactions == (
        MapInteraction(
            "weapon-station",
            "weapon_station",
            position=(304, 208),
            properties=(("kind", "weapon_station"), ("semantic", "interaction")),
        ),
    )
    assert riverside.interactions == ()


def test_schema_semantics_are_identical_under_different_layer_organizations():
    first = load_tmx_definition(FIXTURES / "schema_semantics_a.tmx")
    second = load_tmx_definition(FIXTURES / "schema_semantics_b.tmx")

    assert first.collision == second.collision == (Aabb(10, 20, 40, 10),)
    assert first.spawns == second.spawns == (
        SpawnPoint("survivor-start", (80, 90), role="player"),
    )


def test_production_map_has_first_survival_semantics_without_visual_map_changes():
    definition = load_tmx_definition("Assets/Maps/world_1/world_1.tmx")

    assert definition.spawn_roles() >= {"player", "enemy"}
    players = tuple(spawn for spawn in definition.spawns if spawn.role == "player")
    enemies = tuple(spawn for spawn in definition.spawns if spawn.role == "enemy")
    assert {spawn.actor_kind for spawn in players} == {"soldier"}
    assert len(enemies) == 11
    assert {spawn.actor_kind for spawn in enemies} == {None}
    assert definition.capabilities >= {
        "collision",
        "interactions",
        "interaction:weapon_station",
        "interaction:ammo_station",
        "interaction:health_pack_station",
        "interaction:armor_station",
        "harvestables",
        "harvestable:tree",
        "harvestable:vehicle",
        "construction_anchors",
        "construction_anchor:barricade",
        "playable_area",
    }
    assert definition.interactions[0].interaction_id == "camp-smg"
    assert {item.kind for item in definition.interactions} >= {
        "weapon_station",
        "ammo_station",
        "health_pack_station",
        "armor_station",
    }
    assert len(definition.harvestables) == 120
    assert {item.kind for item in definition.harvestables} == {"tree", "vehicle"}
    assert all("environment" in item.tags for item in definition.harvestables)
    assert definition.construction_anchors[0].anchor_id == "camp-gate"
    assert len(definition.collision) >= 134
    assert any(isinstance(collider, Polygon) for collider in definition.collision)
    assert len(definition.playable_areas) == 1
    assert isinstance(definition.playable_areas[0], Polygon)
    assert {
        tag
        for spawn in definition.spawns
        if spawn.role == "enemy"
        for tag in spawn.tags
    } >= {"entry", "shared", "west", "east", "north", "south"}


def test_spawn_points_and_regions_normalize_without_map_identity_branches():
    crossroads = load_tmx_definition(FIXTURES / "crossroads.tmx")
    survivor = next(spawn for spawn in crossroads.spawns if spawn.role == "survivor")
    enemy = next(spawn for spawn in crossroads.spawns if spawn.role == "enemy")

    assert isinstance(survivor, SpawnPoint)
    assert survivor.position == (64, 240)
    assert isinstance(enemy, SpawnRegion)
    assert enemy.area == Aabb(544, 64, 64, 352)


def test_mode_requirements_report_missing_capabilities_and_roles():
    riverside = load_tmx_definition(FIXTURES / "riverside.tmx")

    survival = riverside.validate(
        MapRequirements(
            capabilities=frozenset(("bounds", "collision", "spawns")),
            spawn_roles=frozenset(("survivor", "enemy")),
        )
    )
    team_mode = riverside.validate(
        MapRequirements(
            capabilities=frozenset(("spawns", "destructibles")),
            spawn_roles=frozenset(("team_a", "team_b")),
        )
    )

    assert survival.compatible is True
    assert team_mode.compatible is False
    assert team_mode.missing_capabilities == {"destructibles"}
    assert team_mode.missing_spawn_roles == {"team_a", "team_b"}


def test_current_incomplete_map_is_valid_when_a_mode_requires_no_spawns():
    report = current_map_definition().validate(
        MapRequirements(capabilities=frozenset(("bounds",)))
    )

    assert report.compatible is True


def test_spawn_semantic_metadata_and_layer_offsets_survive_adaptation(tmp_path):
    source = tmp_path / "semantic-spawns.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Spawns" offsetx="10" offsety="20"><properties>'
        '<property name="semantic" value="spawn"/></properties>'
        '<object id="1" name="north" x="5" y="7" point="1">'
        '<properties><property name="role" value="enemy"/>'
        '<property name="tags" value="outdoor, elevated"/>'
        '<property name="faction" value="horde"/>'
        '<property name="actor_kind" value="walker"/></properties>'
        '</object><object id="2" name="yard" x="20" y="30" '
        'width="40" height="50"><properties>'
        '<property name="role" value="team_a"/></properties></object>'
        '</objectgroup></map>'
    )

    definition = load_tmx_definition(source)
    point, region = definition.spawns

    assert point.position == (15, 27)
    assert point.tags == {"outdoor", "elevated"}
    assert (point.faction, point.actor_kind) == ("horde", "walker")
    assert region.area == Aabb(30, 50, 40, 50)


def test_interaction_regions_preserve_semantics_properties_and_offsets(tmp_path):
    source = tmp_path / "semantic-interactions.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Interactions" offsetx="10" offsety="20"><properties>'
        '<property name="semantic" value="interaction"/></properties>'
        '<object id="1" name="ammo-yard" x="5" y="7" width="40" height="50">'
        '<properties><property name="kind" value="ammo_station"/>'
        '<property name="tags" value="survival, outdoor"/>'
        '<property name="price" value="250"/></properties>'
        '</object></objectgroup></map>'
    )

    (interaction,) = load_tmx_definition(source).interactions

    assert interaction.interaction_id == "ammo-yard"
    assert interaction.kind == "ammo_station"
    assert interaction.area == Aabb(15, 27, 40, 50)
    assert interaction.tags == {"survival", "outdoor"}
    assert dict(interaction.properties)["price"] == "250"


def test_zero_size_tiled_interaction_object_is_adapted_as_a_point(tmp_path):
    source = tmp_path / "point-interaction.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Interactions"><properties><property name="semantic" '
        'value="interaction"/></properties><object id="1" name="pistol" '
        'x="50" y="70"><properties><property name="kind" '
        'value="weapon_station"/></properties></object></objectgroup></map>'
    )

    (interaction,) = load_tmx_definition(source).interactions

    assert interaction.position == (50, 70)


def test_authored_semantics_ignore_presentation_layer_names(tmp_path):
    source = tmp_path / "schema-v2.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Art and Organization"><object id="1" name="wall" '
        'x="10" y="20" width="30" height="40"><properties><property '
        'name="semantic" value="static_blocker"/></properties></object>'
        '<object id="2" name="start" x="50" y="60"><properties>'
        '<property name="semantic" value="spawn"/><property name="role" '
        'value="survivor"/></properties></object></objectgroup></map>'
    )

    definition = load_tmx_definition(source)

    assert definition.collision == (Aabb(10, 20, 30, 40),)
    assert definition.spawns == (SpawnPoint("start", (50, 60), role="survivor"),)


def test_schema_v2_map_metadata_requires_identity_and_supported_version(tmp_path):
    source = tmp_path / "invalid-map-metadata.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<properties><property name="schema_version" type="int" value="2"/>'
        '<property name="map_id" value="test"/></properties></map>'
    )

    with pytest.raises(TmxMapSchemaError, match=r"missing properties: display_name"):
        load_tmx_definition(source)

    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<properties><property name="schema_version" type="int" value="3"/>'
        '<property name="map_id" value="test"/><property '
        'name="display_name" value="Test"/></properties></map>'
    )

    with pytest.raises(TmxMapSchemaError, match=r"unsupported schema_version '3'"):
        load_tmx_definition(source)

    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<properties><property name="schema_version" type="int" value="1"/>'
        '<property name="map_id" value="test"/><property '
        'name="display_name" value="Test"/></properties></map>'
    )

    with pytest.raises(TmxMapSchemaError, match=r"unsupported schema_version '1'"):
        load_tmx_definition(source)


def test_invalid_authored_semantics_report_the_responsible_object(tmp_path):
    source = tmp_path / "invalid-schema-v2.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Any Layer"><object id="9" name="bad-tree" '
        'x="10" y="20" width="30" height="40"><properties><property '
        'name="semantic" value="harvestable"/></properties></object>'
        '</objectgroup></map>'
    )

    with pytest.raises(
        TmxSchemaError, match=r"Any Layer.*9.*bad-tree.*missing properties"
    ):
        load_tmx_definition(source)


def test_authored_static_blocker_rejects_empty_ellipse_geometry(tmp_path):
    source = tmp_path / "empty-blocker.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Props"><object id="8" name="bad-rock" x="5" '
        'y="6"><ellipse/><properties><property name="semantic" '
        'value="static_blocker"/></properties></object></objectgroup></map>'
    )

    with pytest.raises(TmxSchemaError, match=r"Props.*bad-rock.*requires geometry"):
        load_tmx_definition(source)


def test_authored_construction_anchor_requires_a_kind(tmp_path):
    source = tmp_path / "invalid-anchor.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Build"><object id="4" name="missing-kind" x="5" '
        'y="6"><properties><property name="semantic" '
        'value="construction_anchor"/></properties></object></objectgroup></map>'
    )

    with pytest.raises(TmxSchemaError, match=r"Build.*missing-kind.*requires a kind"):
        load_tmx_definition(source)


def test_authored_semantics_reject_duplicate_stable_names_across_layers(tmp_path):
    source = tmp_path / "duplicate-schema-v2.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Collision A"><object id="1" name="wall" '
        'x="0" y="0" width="10" height="10"><properties><property '
        'name="semantic" value="static_blocker"/></properties></object>'
        '</objectgroup><objectgroup name="Collision B"><object id="2" '
        'name="wall" x="20" y="20" width="10" height="10"><properties>'
        '<property name="semantic" value="static_blocker"/></properties>'
        '</object></objectgroup></map>'
    )

    with pytest.raises(TmxSchemaError, match=r"Collision B.*duplicate static_blocker"):
        load_tmx_definition(source)


def test_authored_harvestable_requires_valid_numeric_durability_and_yield(tmp_path):
    source = tmp_path / "invalid-harvest-numbers.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Props"><object id="3" name="oak" x="0" y="0" '
        'width="10" height="10"><properties><property name="semantic" '
        'value="harvestable"/><property name="kind" value="tree"/>'
        '<property name="durability" value="broken"/><property '
        'name="resource_id" value="wood"/><property name="resource_yield" '
        'value="10"/><property name="required_tool_capability" '
        'value="harvest"/></properties></object></objectgroup></map>'
    )

    with pytest.raises(TmxSchemaError, match=r"Props.*oak.*durability must be numeric"):
        load_tmx_definition(source)


def test_fence_polyline_adapts_to_a_solid_clearance_collider(tmp_path):
    source = tmp_path / "fence.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Fence"><properties><property name="semantic" '
        'value="static_blocker"/><property name="clearance" value="32"/>'
        '</properties><object id="1" x="10" y="20">'
        '<polyline points="0,0 100,0"/></object></objectgroup></map>'
    )

    (fence,) = load_tmx_definition(source).collision

    assert isinstance(fence, Polygon)
    assert fence.points == ((10, 36), (110, 36), (110, 4), (10, 4))


def test_tree_collider_layer_preserves_authored_non_rectangular_shapes(tmp_path):
    source = tmp_path / "tree-colliders.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Tree Colliders"><properties><property name="semantic" '
        'value="static_blocker"/></properties><object id="1" x="10" y="20">'
        '<polygon points="0,0 30,0 15,25"/></object></objectgroup></map>'
    )

    (collider,) = load_tmx_definition(source).collision

    assert collider == Polygon(((10, 20), (40, 20), (25, 45)))


def test_placed_tree_inherits_and_scales_its_tileset_collision_shape(tmp_path):
    source = tmp_path / "tile-collision.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<tileset firstgid="1" name="trees"><tile id="0">'
        '<image source="tree.png" width="100" height="200"/>'
        '<objectgroup><object x="20" y="100"><polygon '
        'points="0,0 60,0 30,80"/></object></objectgroup>'
        '</tile></tileset><objectgroup name="Placed Trees" offsetx="5" offsety="7">'
        '<properties><property name="semantic" value="harvestable"/>'
        '<property name="kind" value="tree"/><property name="durability" '
        'value="100"/><property name="resource_id" value="wood"/>'
        '<property name="resource_yield" value="1"/><property '
        'name="required_tool_capability" value="harvest"/><property '
        'name="collision_source" value="tile"/></properties><object id="1" '
        'type="tree" gid="1" '
        'x="10" y="20" width="50" height="100"/></objectgroup></map>'
    )

    definition = load_tmx_definition(source)

    assert definition.collision == (Polygon(((25, 77), (55, 77), (40, 117))),)


def test_authored_harvestable_can_request_its_tile_collision_footprint(tmp_path):
    source = tmp_path / "semantic-tile-collision.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<tileset firstgid="1"><tile id="0"><image source="tree.png" '
        'width="100" height="100"/><objectgroup><object x="20" y="30" '
        'width="40" height="50"/></objectgroup></tile></tileset>'
        '<objectgroup name="Props"><object id="1" name="oak" gid="1" '
        'x="10" y="20" width="50" height="50"><properties><property '
        'name="semantic" value="harvestable"/><property name="kind" '
        'value="tree"/><property name="durability" value="100"/><property '
        'name="resource_id" value="wood"/><property name="resource_yield" '
        'value="5"/><property name="required_tool_capability" value="harvest"/>'
        '<property name="collision_source" value="tile"/></properties>'
        '</object></objectgroup></map>'
    )

    (collision,) = load_tmx_definition(source).collision

    assert collision == Aabb(20, 35, 20, 25)


def test_harvestable_regions_preserve_semantics_properties_and_offsets(tmp_path):
    source = tmp_path / "semantic-harvestables.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Harvestables" offsetx="10" offsety="20"><properties>'
        '<property name="semantic" value="harvestable"/><property name="resource_id" '
        'value="wood"/><property name="resource_yield" value="1"/></properties>'
        '<object id="1" name="oak-1" x="5" y="7" width="40" height="50">'
        '<properties><property name="kind" value="tree"/>'
        '<property name="durability" value="200"/>'
        '<property name="required_tool_capability" value="harvest"/>'
        '</properties></object></objectgroup></map>'
    )

    (harvestable,) = load_tmx_definition(source).harvestables

    assert harvestable == MapHarvestable(
        "oak-1",
        "tree",
        area=Aabb(15, 27, 40, 50),
        properties=(
                ("durability", "200"),
                ("kind", "tree"),
                ("required_tool_capability", "harvest"),
                ("resource_id", "wood"),
                ("resource_yield", "1"),
                ("semantic", "harvestable"),
        ),
    )
    assert "harvestable:tree" in load_tmx_definition(source).capabilities


def test_world_creation_uses_explicit_map_data_without_identity_branches(display):
    first = MapDefinition(
        "compact",
        "Compact",
        CURRENT_PRESENTATION,
        (4000, 3000),
        (Aabb(100, 100, 50, 50),),
        frozenset(("bounds", "collision")),
    )
    second = MapDefinition(
        "wide",
        "Wide",
        CURRENT_PRESENTATION,
        (8000, 3500),
        (),
        frozenset(("bounds",)),
    )

    compact = Session(Viewport(WINDOW), map_definition=first)
    wide = Session(Viewport(WINDOW), map_definition=second)

    assert compact.map_definition is first
    assert wide.map_definition is second
    assert compact.world_size == first.size
    assert wide.world_size == second.size
    assert tuple(compact._world_obstacles()) == first.collision
    assert tuple(wide._world_obstacles()) == ()
