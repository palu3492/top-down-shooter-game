"""Production-neutral map definitions from incomplete Tiled maps."""

from pathlib import Path

from shooter.map_definition import MapDefinition, load_tmx_definition
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
    assert crossroads.capabilities == riverside.capabilities == {
        "bounds",
        "collision",
    }
    assert crossroads.collision != riverside.collision


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
