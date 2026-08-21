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
from shooter.input_adapter import PygameInputAdapter
from shooter.scenes import Scene
from shooter.session import Session

PAUSE = "PAUSE"


class GameplayScene(Scene):
    title = "GAME"
    opaque = True
    simulates = True

    def __init__(self, window, manager=None, rules=None):
        super().__init__(window, manager)
        self.session = Session(window) if rules is None else Session(window, rules)
        self.reported = False
        self.input_adapter = PygameInputAdapter()

    def open(self):
        """Nothing to build: the session is the scene, and it outlives being
        covered by a menu."""

    def close(self):
        """Nothing to tear down. Dropping the scene drops the session with it."""

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
