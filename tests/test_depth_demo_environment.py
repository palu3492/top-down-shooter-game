import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from shooter.demos.environment_map import EnvironmentMap, PROP_DEFINITIONS


def setup_module():
    pygame.init()
    pygame.display.set_mode((1, 1))


def teardown_module():
    pygame.quit()


def test_layout_is_dense_but_leaves_open_center():
    environment = EnvironmentMap()
    assert len(environment.props) >= 20
    assert len(environment.decals) >= 40
    center = pygame.Rect(450, 285, 180, 150)
    assert sum(center.colliderect(rect) for rect in environment.footprints) <= 1


def test_every_placed_prop_has_asset_anchor_and_collision_metadata():
    environment = EnvironmentMap()
    for prop in environment.props:
        definition = PROP_DEFINITIONS[prop.kind]
        assert definition.anchor == (0.5, 1.0)
        assert definition.footprint[0] > 0 and definition.footprint[1] > 0
        assert prop.footprint.midbottom == tuple(map(round, prop.position))


def test_depth_entries_are_sortable_and_tall_props_fade():
    environment = EnvironmentMap()
    entries = sorted(environment.depth_entries(), key=lambda entry: entry.ground_y)
    assert entries[0].ground_y <= entries[-1].ground_y
    tree = next(prop for prop in environment.props if prop.kind.startswith("tree"))
    player = pygame.Vector2(tree.position.x, tree.position.y - 20)
    assert tree.obscures(player)


def test_blocked_uses_small_ground_footprints_not_full_artwork():
    environment = EnvironmentMap()
    prop = environment.props[0]
    assert environment.blocked(prop.position, 8)
    visual_top = pygame.Vector2(prop.position.x, prop.image_rect.top + 5)
    assert not environment.blocked(visual_top, 3)
