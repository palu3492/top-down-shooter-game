"""A test-side TMX contract for the future production map adapter."""

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "maps"
MAPS = (FIXTURES / "crossroads.tmx", FIXTURES / "riverside.tmx")
MODE_SPAWNS = {
    "zombie_survival": frozenset(("survivor", "enemy")),
    "team_deathmatch": frozenset(("team_a", "team_b")),
}


@dataclass(frozen=True)
class SpawnContract:
    role: str
    shape: str


@dataclass(frozen=True)
class MapContract:
    map_id: str
    display_name: str
    schema_version: int
    size: tuple[int, int]
    supported_modes: frozenset[str]
    collision_shapes: tuple[str, ...]
    spawns: tuple[SpawnContract, ...]
    interactions: tuple[str, ...]

    def supports(self, mode):
        roles = frozenset(spawn.role for spawn in self.spawns)
        return mode in self.supported_modes and MODE_SPAWNS[mode] <= roles


def properties(element):
    found = element.find("properties")
    if found is None:
        return {}
    return {item.attrib["name"]: item.attrib.get("value", "") for item in found}


def object_shape(item):
    if item.find("polygon") is not None:
        return "polygon"
    if item.find("ellipse") is not None:
        return "ellipse"
    if item.attrib.get("point") == "1":
        return "point"
    return "rectangle"


def objects_in(root, layer_name):
    layer = next(
        (
            layer
            for layer in root.findall("objectgroup")
            if layer.attrib["name"] == layer_name
        ),
        None,
    )
    return () if layer is None else tuple(layer.findall("object"))


def load_contract(path):
    root = ElementTree.parse(path).getroot()
    metadata = properties(root)
    required = {"map_id", "display_name", "schema_version", "supported_modes"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"{path.name} is missing map properties: {sorted(missing)}")

    collisions = objects_in(root, "Collision")
    spawn_objects = objects_in(root, "Spawns")
    if not collisions or not spawn_objects:
        raise ValueError(f"{path.name} requires Collision and Spawns objects")

    return MapContract(
        map_id=metadata["map_id"],
        display_name=metadata["display_name"],
        schema_version=int(metadata["schema_version"]),
        size=(
            int(root.attrib["width"]) * int(root.attrib["tilewidth"]),
            int(root.attrib["height"]) * int(root.attrib["tileheight"]),
        ),
        supported_modes=frozenset(metadata["supported_modes"].split(",")),
        collision_shapes=tuple(object_shape(item) for item in collisions),
        spawns=tuple(
            SpawnContract(properties(item)["role"], object_shape(item))
            for item in spawn_objects
        ),
        interactions=tuple(
            properties(item)["kind"] for item in objects_in(root, "Interactions")
        ),
    )


@pytest.mark.parametrize("path", MAPS)
def test_each_map_normalizes_to_the_same_contract(path):
    contract = load_contract(path)

    assert contract.map_id
    assert contract.display_name
    assert contract.schema_version == 1
    assert all(dimension > 0 for dimension in contract.size)
    assert contract.collision_shapes
    assert {spawn.role for spawn in contract.spawns} >= {"survivor", "enemy"}
    assert contract.supports("zombie_survival") is True


def test_map_identity_does_not_control_normalization():
    crossroads, riverside = map(load_contract, MAPS)

    assert crossroads.map_id != riverside.map_id
    assert crossroads.size != riverside.size
    assert crossroads.supports("team_deathmatch") is True
    assert riverside.supports("team_deathmatch") is False
    assert crossroads.interactions == ("weapon_station",)
    assert riverside.interactions == ()


def test_required_map_metadata_is_validated(tmp_path):
    invalid = tmp_path / "invalid.tmx"
    invalid.write_text(
        '<map width="1" height="1" tilewidth="32" tileheight="32">'
        '<objectgroup name="Collision"><object id="1"/></objectgroup>'
        '<objectgroup name="Spawns"><object id="2"/></objectgroup>'
        "</map>"
    )

    with pytest.raises(ValueError, match="missing map properties"):
        load_contract(invalid)
