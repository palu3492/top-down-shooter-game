"""The application shell owns selection and one disposable active Match."""

import pytest

from shooter import game
from shooter.application import MatchHost
from shooter.gameplay import GameplayScene
from shooter.map_definition import MapDefinition, MapRequirements
from shooter.match import DISPOSED, IncompatibleMatchError
from shooter.match_configuration import (
    MapCatalog,
    MatchConfiguration,
    ModeCatalog,
    ModeDescriptor,
)
from shooter.scenes import Scene, SceneStack
from shooter.settings import Settings
from shooter.systems import levels
from shooter.ui import menu
from shooter.ui.menu import PauseScreen
from shooter.viewport import Viewport


def catalogs():
    mode = ModeDescriptor(
        "duel",
        "Duel",
        "Two teams",
        MapRequirements(capabilities=frozenset(("bounds", "team_spawns"))),
        (("red", "blue"),),
    )
    compatible = MapDefinition(
        "arena",
        "Arena",
        "arena.tmx",
        (1000, 800),
        capabilities=frozenset(("bounds", "team_spawns")),
    )
    incompatible = MapDefinition(
        "empty",
        "Empty",
        "empty.tmx",
        (1000, 800),
        capabilities=frozenset(("bounds",)),
    )
    return ModeCatalog((mode,)), MapCatalog((compatible, incompatible))


class SelectionRoot(Scene):
    def open(self):
        pass


def test_selection_is_validated_before_any_match_state_is_constructed():
    modes, maps = catalogs()
    original = MatchConfiguration("duel", "arena", 1)
    host = MatchHost(modes, maps, original)

    with pytest.raises(IncompatibleMatchError):
        host.start(MatchConfiguration("duel", "empty", 2))

    assert host.active_match is None
    assert host.configuration is original


def test_leave_and_restart_replace_all_match_scoped_state():
    modes, maps = catalogs()
    host = MatchHost(modes, maps, MatchConfiguration("duel", "arena", 1))
    first = host.start()
    first.entities.register(object())

    host.leave()

    assert first.state == DISPOSED
    assert host.active_match is None

    second = host.start(MatchConfiguration("duel", "arena", 2))
    assert second is host.active_match
    assert second is not first
    assert second.configuration.seed == 2
    assert len(second.entities) == 0


def test_select_changes_pending_configuration_without_allocating_a_match():
    modes, maps = catalogs()
    host = MatchHost(modes, maps, MatchConfiguration("duel", "arena", 1))
    selected = MatchConfiguration("duel", "arena", 99)

    resolved = host.select(selected)

    assert resolved.compatible
    assert host.configuration is selected
    assert host.active_match is None


def test_covering_gameplay_preserves_match_but_removing_it_disposes(display):
    window = Viewport((1080, 720))
    stack = SceneStack(window)
    host = MatchHost()
    match = host.start()
    stack.push(
        GameplayScene(
            window,
            stack.manager,
            match_owner=match,
            match_host=host,
        )
    )

    stack.push(PauseScreen(window, stack.manager))
    assert host.active_match is match
    stack.pop()
    assert host.active_match is match

    stack.pop()
    assert match.state == DISPOSED
    assert host.active_match is None


def test_application_can_leave_selection_and_start_again_without_restart(display):
    window = Viewport((1080, 720))
    stack = SceneStack(window)
    stack.push(SelectionRoot(window, stack.manager))
    host = MatchHost()

    game.start_level(stack, window, levels.FIRST, match_host=host)
    first = host.active_match
    assert isinstance(stack.top, GameplayScene)

    game.route(menu.END_GAME, stack, window, Settings(), match_host=host)
    assert isinstance(stack.top, SelectionRoot)
    assert first.state == DISPOSED

    game.start_level(stack, window, levels.FIRST, match_host=host)
    assert isinstance(stack.top, GameplayScene)
    assert host.active_match is not first
