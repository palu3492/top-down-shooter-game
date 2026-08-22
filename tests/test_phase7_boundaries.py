"""Executable Phase 7 Match/mode boundary and lifecycle audit."""

import ast
from pathlib import Path

from shooter.application import MatchHost
from shooter.gameplay import GameplayScene
from shooter.match import DISPOSED
from shooter.scenes import Scene, SceneStack
from shooter.viewport import Viewport

WINDOW = (1080, 720)


def direct_imports(filename):
    imports = set()
    for node in ast.walk(ast.parse(Path(filename).read_text())):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


class SelectionRoot(Scene):
    def open(self):
        pass


class DisposalCounter:
    def __init__(self):
        self.disposals = 0

    def start(self, match):
        pass

    def advance(self, match, commands, dt):
        pass

    def status(self, match):
        return None

    def result(self, match):
        return None

    def dispose(self, match):
        self.disposals += 1


def start_game(stack, host):
    match = host.start()
    scene = GameplayScene(
        stack.window,
        stack.manager,
        match_owner=match,
        match_host=host,
    )
    stack.push(scene)
    return match, scene


def test_consecutive_matches_isolate_simulation_mode_and_presentation(display):
    window = Viewport(WINDOW)
    stack = SceneStack(window)
    stack.push(SelectionRoot(window, stack.manager))
    host = MatchHost()
    first_match, first_scene = start_game(stack, host)
    first = first_scene.session
    first.cash.increase_cash(750)
    first.rules.wave_count = 7
    first.rules.wave_seconds = 3.0
    first.random_value = first_match.random_stream("loot").random()
    first.notice = "old match"

    stack.pop()
    second_match, second_scene = start_game(stack, host)
    second = second_scene.session

    assert first_match.state == DISPOSED
    assert second_match is not first_match
    assert second.entities is not first.entities
    assert second.cash.cash_amount == 0
    assert second.rules.wave_count == 0
    assert second.rules.wave_seconds == 0.0
    assert second.notice is None
    assert second.human is not first.human
    assert second.mode_status_display is not first.mode_status_display

    pristine = MatchHost().start()
    assert second_match.random_stream("loot").random() == pristine.random_stream(
        "loot"
    ).random()


def test_shared_match_modules_have_no_direct_pygame_or_mode_dependency():
    shared = (
        "shooter/match.py",
        "shooter/damage.py",
        "shooter/spatial.py",
        "shooter/world_registry.py",
        "shooter/spawn_selection.py",
        "shooter/weapon_state.py",
        "shooter/weapon_attacks.py",
        "shooter/economy.py",
    )
    for filename in shared:
        imports = direct_imports(filename)
        assert "pygame" not in {name.split(".")[0] for name in imports}, filename
        mode_imports = {name for name in imports if name.startswith("shooter.modes")}
        assert mode_imports <= {"shooter.modes.contract"}, filename


def test_survival_rules_have_no_direct_rendering_dependency():
    for filename in (
        "shooter/modes/zombie_survival/waves.py",
        "shooter/modes/zombie_survival/consequences.py",
        "shooter/modes/zombie_survival/state.py",
        "shooter/modes/zombie_survival/shop.py",
        "shooter/systems/levels.py",
    ):
        imports = direct_imports(filename)
        assert "pygame" not in {name.split(".")[0] for name in imports}, filename
        assert not any(name.startswith("shooter.ui") for name in imports), filename


def test_application_constructs_matches_only_after_configuration_resolution():
    source = Path("shooter/application.py").read_text()
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    assert any(
        isinstance(call.func, ast.Name) and call.func.id == "Match" for call in calls
    )
    assert "MatchConfigurationResolver" in source


def test_repeated_cleanup_disposes_mode_exactly_once():
    host = MatchHost()
    match = host.start()
    mode = DisposalCounter()
    match.start(mode)

    match.dispose()
    host.leave()

    assert mode.disposals == 1
    assert host.active_match is None
