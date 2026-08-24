"""The scene a game is played in.

It owns a `Session` for as long as it is on the stack. Pushing it starts a game
and popping it ends one, which is all "start game" and "end game" have to mean
now that the world is an object rather than a function's locals.

`open` and `close` do nothing on purpose. They are how the interface layer
builds and kills widgets, and this scene has none -- so pause can be pushed on
top and popped off again without the world noticing.

The crosshair and the frame counter are not drawn here. Both belong to the
application: the crosshair replaces the system pointer only while this scene is
the one being played, and drawing it from here would put it under the pause
veil, which is the ghost AT21 removed.
"""

import pygame

from shooter import config
from shooter.background import TiledBackground
from shooter.camera import FollowCamera
from shooter.commands import (
    FIRE, INTERACT, RELOAD, SELECT_SLOT, USE_ARMOR_PLATE, USE_HEALTH_PACK, USE_TOOL,
)
from shooter.input_adapter import PygameInputAdapter
from shooter.map_definition import SpawnPoint, SpawnRegion, current_map_definition
from shooter.modes.sandbox import AttackActor, MoveActor
from shooter.modes.zombie_survival import (
    FireSurvivorWeapon,
    HoldSurvivorWeapon,
    InteractSurvivor,
    MoveSurvivor,
    ReloadSurvivorWeapon,
    SelectSurvivorWeapon,
    UseSurvivorTool,
    UseHealthPack,
    UseArmorPlate,
)
from shooter.scenes import Scene
from shooter.session import Session
from shooter.ui.snapshot_presentation import SnapshotPresentation
from shooter.ui.map_semantics import MapSemanticsRenderer
from shooter.ui.survival_tuner import SurvivalTuner
from shooter.world_collision import Aabb
from shooter.weapon_state import EquippedWeapon

PAUSE = "PAUSE"


class GameplayScene(Scene):
    title = "GAME"
    opaque = True
    simulates = True

    def __init__(
        self,
        window,
        manager=None,
        rules=None,
        map_definition=None,
        match_owner=None,
        match_host=None,
    ):
        super().__init__(window, manager)
        selected_map = map_definition or current_map_definition()
        if rules is None:
            self.session = Session(
                window, map_definition=selected_map, match_owner=match_owner
            )
        else:
            self.session = Session(
                window,
                rules,
                map_definition=selected_map,
                match_owner=match_owner,
            )
        self.reported = False
        self.match_host = match_host
        self.input_adapter = PygameInputAdapter()

    def open(self):
        """Nothing to build: the session is the scene, and it outlives being
        covered by a menu."""

    def close(self):
        """Nothing to tear down. Dropping the scene drops the session with it."""

    def dispose(self):
        if self.match_host is not None:
            self.match_host.leave()
        else:
            self.session.match.dispose()

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return PAUSE
        command = self.input_adapter.action_for(event)
        if command is not None:
            self.session.apply_action(command)
        return None

    def update(self, inputs, dt=config.SIM_DT):
        if hasattr(inputs, "move"):
            self.session.step_controls(inputs, dt)
            return
        self.session.aim_at(inputs.pointer)
        self.session.step(inputs.pressed, dt, inputs.trigger)

    def tick(self, seconds):
        """Report an ending once.

        The outcome stays true for every frame after it happens, so without
        this the shell would be handed a result screen sixty times a second.
        """
        if self.reported or self.session.outcome is None:
            return None
        self.reported = True
        return self.session.outcome

    def draw(self, surface, alpha):
        self.session.draw(surface, alpha)


class SnapshotGameplayScene(Scene):
    """TMX and snapshot presentation shared by neutral runtime modes."""

    opaque = True
    simulates = True

    def __init__(self, window, manager, match_owner, match_host=None):
        super().__init__(window, manager)
        self.match = match_owner
        self.mode = match_owner.mode
        self.match_host = match_host
        self.presenter = SnapshotPresentation()
        self.map_semantics = MapSemanticsRenderer()
        self.reported = False
        self.background = TiledBackground(
            self.match.map_definition.presentation_source
        )
        self.input_adapter = PygameInputAdapter()
        target_id = next(
            entity_id
            for entity_id in self.match.entities.ids()
            if "player" in self.match.entities.tags_for(entity_id)
        )
        self.presentation_camera = FollowCamera(
            self.window,
            self.match.map_definition.size,
            self.match.spatial,
            target_id,
        )

    @property
    def camera(self):
        return self.presentation_camera.resize(self.window)

    def open(self):
        pass

    def close(self):
        pass

    def dispose(self):
        if self.match_host is not None:
            self.match_host.leave()
        else:
            self.match.dispose()

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return PAUSE
        return None

    def draw(self, surface, alpha):
        camera = self.camera
        self.background.draw(surface, *camera)
        self.map_semantics.draw(surface, self.match.map_definition, camera)
        self.presenter.draw(surface, self.match.snapshot(), camera)

    def tick(self, seconds):
        """Report a terminal Match result once to the application router."""
        outcome = self.match.result
        if self.reported or outcome is None:
            return None
        self.reported = True
        return outcome


class SandboxGameplayScene(SnapshotGameplayScene):
    """Visible shell for a neutral Sandbox Match and its snapshots."""

    title = "SANDBOX"

    def handle(self, event):
        routed = super().handle(event)
        if routed is not None:
            return routed
        command = self.input_adapter.action_for(event)
        if command is not None and command.action == FIRE:
            red = self.mode.actor_ids.get("red")
            blue = self.mode.actor_ids.get("blue")
            if red is not None and blue is not None:
                self.match.advance(0.0, (AttackActor(red, blue, 10),))
        return None

    def update(self, inputs, dt=config.SIM_DT):
        red = self.mode.actor_ids.get("red")
        commands = () if red is None else (MoveActor(red, inputs.move),)
        self.match.advance(dt, commands)



class SurvivalGameplayScene(SnapshotGameplayScene):
    """Visible shell for the shared-runtime Zombie Survival slice."""

    title = "ZOMBIE SURVIVAL"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tuner = SurvivalTuner(self.mode.balance)
        self.tuning = False
        self.fire_pointer = None

    def handle(self, event):
        routed = super().handle(event)
        if routed is not None:
            return routed
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.tuning = not self.tuning
            return None
        if self.tuning and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_2):
                definition = (
                    self.mode.pistol if event.key == pygame.K_1 else self.mode.smg
                )
                self._grant_debug_weapon(definition)
                return None
            self.tuner.handle(event)
            return None
        if event.type == pygame.MOUSEMOTION:
            self.fire_pointer = event.pos
        command = self.input_adapter.action_for(event)
        if command is not None and command.action == FIRE:
            self.fire_pointer = event.pos
            player = self.match.spatial.get(self.mode.player_id).transform
            camera_x, camera_y = self.camera
            world_pointer = (event.pos[0] - camera_x, event.pos[1] - camera_y)
            aim = (world_pointer[0] - player.x, world_pointer[1] - player.y)
            self.match.advance(0.0, (FireSurvivorWeapon(aim),))
        elif command is not None and command.action == RELOAD:
            self.match.advance(0.0, (ReloadSurvivorWeapon(),))
        elif command is not None and command.action == INTERACT:
            self.match.advance(0.0, (InteractSurvivor(),))
        elif command is not None and command.action == USE_TOOL:
            self.match.advance(0.0, (UseSurvivorTool(),))
        elif command is not None and command.action == USE_HEALTH_PACK:
            self.match.advance(0.0, (UseHealthPack(),))
        elif command is not None and command.action == USE_ARMOR_PLATE:
            self.match.advance(0.0, (UseArmorPlate(),))
        elif (
            command is not None
            and command.action == SELECT_SLOT
            and command.value is not None
        ):
            self.match.advance(0.0, (SelectSurvivorWeapon(command.value),))
        return None

    def _grant_debug_weapon(self, definition):
        loadout = self.mode.loadouts.get(self.mode.player_id)
        if loadout is None:
            return
        weapon = loadout.find(
            lambda held: held.definition.definition_id == definition.definition_id
        )
        if weapon is None:
            if loadout.full:
                entries = list(loadout)
                entries[loadout.selected_index] = EquippedWeapon(definition)
                loadout.replace(entries, selected=loadout.selected_index)
                weapon = loadout.selected
            else:
                weapon = loadout.add(EquippedWeapon(definition), select=True)
        else:
            loadout.select_entry(weapon)
        self.mode.tool_equipped = False
        weapon_name = definition.definition_id.replace("survivor_", "").upper()
        self.tuner.notice = f"Debug equipped {weapon_name}."

    def draw(self, surface, alpha):
        super().draw(surface, alpha)
        if self.tuning:
            self.tuner.draw(surface)
        else:
            self.tuner.draw_hint(surface)

    def update(self, inputs, dt=config.SIM_DT):
        commands = [MoveSurvivor(inputs.move)]
        if getattr(inputs, "trigger_held", getattr(inputs, "trigger", False)):
            pointer = self.fire_pointer or getattr(inputs, "pointer", None)
            if pointer is None:
                aim = inputs.aim
            else:
                player = self.match.spatial.get(self.mode.player_id).transform
                camera_x, camera_y = self.camera
                aim = (
                    pointer[0] - camera_x - player.x,
                    pointer[1] - camera_y - player.y,
                )
            commands.append(HoldSurvivorWeapon(aim))
        self.match.advance(dt, commands)


def sandbox_spawn_sources(map_definition):
    """Use authored team starts when present, otherwise an explicit dev fallback."""
    authored = tuple(
        source
        for source in map_definition.spawns
        if source.role == "player" and source.faction in {"red", "blue"}
    )
    if {source.faction for source in authored} >= {"red", "blue"}:
        return authored
    width, height = map_definition.size
    return (
        SpawnPoint(
            "sandbox-red",
            (width / 2 - 120, height / 2),
            role="player",
            faction="red",
            actor_kind="soldier",
        ),
        SpawnPoint(
            "sandbox-blue",
            (width / 2 + 120, height / 2),
            role="player",
            faction="blue",
            actor_kind="soldier",
        ),
    )


def survival_spawn_sources(map_definition):
    """Use authored Survival starts or a named central migration fallback."""
    player = tuple(
        source
        for source in map_definition.spawns
        if source.role == "player" and source.faction == "survivors"
    )
    enemies = tuple(
        source
        for source in map_definition.spawns
        if source.role == "enemy" and source.faction == "horde"
    )
    if player and enemies:
        return player + enemies
    width, height = map_definition.size
    return (
        SpawnPoint(
            "survival-player",
            (width / 2, height / 2),
            role="player",
            faction="survivors",
            actor_kind="soldier",
        ),
        SpawnRegion(
            "survival-horde",
            Aabb(width / 2 - 450, height / 2 - 300, 900, 600),
            role="enemy",
            faction="horde",
            actor_kind="walker",
        ),
    )
