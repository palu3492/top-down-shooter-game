"""Stable entity identity independent of pygame sprite groups."""

from shooter.entities.zombie import Zombie
from shooter.session import Session
from shooter.spatial import Box, Transform
from shooter.viewport import Viewport
from shooter.world_registry import WorldRegistry

WINDOW = (1080, 720)


def test_registry_assigns_stable_primitive_ids_and_supports_tags():
    registry = WorldRegistry()
    player = object()
    enemy = object()

    player_id = registry.register(player, ("actor", "player"))
    enemy_id = registry.register(enemy, ("actor", "enemy"))

    assert isinstance(player_id, int)
    assert registry.register(player) == player_id
    assert registry.get(enemy_id) is enemy
    assert registry.ids("actor") == (player_id, enemy_id)
    assert registry.entities("enemy") == (enemy,)


def test_removed_ids_are_not_reused():
    registry = WorldRegistry()
    first_id = registry.register(object())

    registry.remove(first_id)
    second_id = registry.register(object())

    assert second_id > first_id
    assert first_id not in registry


def test_registries_are_match_scoped_and_share_no_state():
    first = WorldRegistry()
    second = WorldRegistry()

    first_entity = object()
    second_entity = object()

    assert first.register(first_entity) == 1
    assert second.register(second_entity) == 1
    assert first.entities() == (first_entity,)
    assert second.entities() == (second_entity,)


def test_session_bridges_player_and_enemy_lifecycle(display, cash):
    session = Session(Viewport(WINDOW))
    enemy = Zombie(WINDOW, cash)
    session.zombies.add(enemy)

    session._sync_enemy_registry()
    enemy_id = session.entities.id_for(enemy)

    assert session.entities.get(session.player_id) is session.human
    assert session.entities.ids("enemy") == (enemy_id,)
    assert session.spatial.get(enemy_id).transform == Transform(
        enemy.world_x + enemy.rect.width / 2,
        enemy.world_y + enemy.rect.height / 2,
    )
    assert session.spatial.get(enemy_id).collision == Box(*enemy.rect.size)

    enemy.kill()
    session._sync_enemy_registry()

    assert enemy_id not in session.entities
    assert session.entities.id_for(enemy) is None
    assert enemy_id not in session.spatial
