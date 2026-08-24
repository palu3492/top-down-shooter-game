"""Production-neutral map definitions from incomplete Tiled maps."""

from pathlib import Path

from shooter.map_definition import (
    MapDefinition,
    MapHarvestable,
    MapInteraction,
    MapRequirements,
    SpawnPoint,
    SpawnRegion,
    current_map_definition,
    load_tmx_definition,
)
from shooter.session import Session
from shooter.viewport import Viewport
from shooter.world_collision import Aabb

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
            properties=(("kind", "weapon_station"),),
        ),
    )
    assert riverside.interactions == ()


def test_production_map_has_first_survival_semantics_without_visual_map_changes():
    definition = load_tmx_definition("Assets/Maps/world_1/world_1.tmx")

    assert definition.spawn_roles() >= {"player", "enemy"}
    assert {spawn.actor_kind for spawn in definition.spawns} >= {
        "soldier",
        "walker",
        "runner",
        "breaker",
    }
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
    assert len(definition.collision) >= 138
    assert {
        tag
        for spawn in definition.spawns
        if spawn.role == "enemy"
        for tag in spawn.tags
    } >= {"entry", "west", "east", "north", "south", "southwest"}


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
        '<objectgroup name="Spawns" offsetx="10" offsety="20">'
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
        '<objectgroup name="Interactions" offsetx="10" offsety="20">'
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
        '<objectgroup name="Interactions"><object id="1" name="pistol" '
        'x="50" y="70"><properties><property name="kind" '
        'value="weapon_station"/></properties></object></objectgroup></map>'
    )

    (interaction,) = load_tmx_definition(source).interactions

    assert interaction.position == (50, 70)


def test_harvestable_regions_preserve_semantics_properties_and_offsets(tmp_path):
    source = tmp_path / "semantic-harvestables.tmx"
    source.write_text(
        '<map width="10" height="10" tilewidth="32" tileheight="32">'
        '<objectgroup name="Harvestables" offsetx="10" offsety="20">'
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
