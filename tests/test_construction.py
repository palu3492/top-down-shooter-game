"""Barricade recipes spend match resources transactionally at authored anchors."""

from shooter.construction import BUILT, FULL_HEALTH, REPAIRED, ConstructionService
from shooter.map_definition import MapConstructionAnchor
from shooter.resources import ResourceInventory
from shooter.world_collision import Aabb


def test_build_and_repair_spend_authored_recipes_transactionally():
    anchor = MapConstructionAnchor(
        "gate",
        "barricade",
        position=(0, 0),
        properties=(
            ("build_cost", "wood:4,metal:2"),
            ("max_health", "100"),
            ("repair_cost", "wood:1"),
        ),
    )
    state = ConstructionService().create_states((anchor,))["gate"]
    resources = ResourceInventory((("wood", 5), ("metal", 2)))
    service = ConstructionService()

    built = service.build_or_repair(state, resources)
    state.health = 40
    repaired = service.build_or_repair(state, resources)
    full = service.build_or_repair(state, resources)

    assert (built.reason, built.health) == (BUILT, 100)
    assert resources.snapshot() == (("metal", 0), ("wood", 0))
    assert (repaired.reason, repaired.health) == (REPAIRED, 100)
    assert full.reason == FULL_HEALTH


def test_built_area_blocks_until_enemy_damage_destroys_it():
    anchor = MapConstructionAnchor(
        "gate",
        "barricade",
        area=Aabb(40, 40, 20, 20),
        properties=(("build_cost", "wood:1"), ("max_health", "20")),
    )
    service = ConstructionService()
    state = service.create_states((anchor,))["gate"]
    service.build_or_repair(state, ResourceInventory((("wood", 1),)))

    assert service.collision_obstacles({"gate": state}) == (Aabb(40, 40, 20, 20),)
    assert service.damage(state, 10) is False
    assert state.health == 10
    assert service.damage(state, 10) is True
    assert service.collision_obstacles({"gate": state}) == ()
