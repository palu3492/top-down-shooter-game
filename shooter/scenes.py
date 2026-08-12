"""Everything the game can be showing, and the stack that owns it.

AT21 built a stack that deliberately excluded the one scene that mattered,
which is why `Screen` carried a `covers_game` flag naming the thing it could not
hold. With gameplay on the stack that flag is just opacity: a scene either hides
what is under it or it does not, and pause stops being a special case.

Two properties decide how the loop treats a scene:

`opaque`   -- whether anything below still needs drawing.
`simulates` -- whether the fixed timestep advances while it is on top. Only
              gameplay says yes, which is the whole of what pausing means.
"""

from pathlib import Path

import pygame
import pygame_gui

THEME = Path(__file__).parent / "ui" / "theme.json"

VEIL = (0, 0, 0, 170)
BACKDROP = (22, 26, 17)


def build_manager(window):
    return pygame_gui.UIManager(window, str(THEME))


class Scene:
    """One layer of the game."""

    title = ""
    opaque = True
    simulates = False

    def __init__(self, window, manager):
        self.window = window
        self.manager = manager
        self.elements = []

    def open(self):
        raise NotImplementedError

    def add(self, element):
        """Every widget a scene builds goes through here, so closing the scene
        is what kills it rather than whoever remembered to say so."""
        self.elements.append(element)
        return element

    def close(self):
        for element in self.elements:
            element.kill()
        self.elements.clear()

    def handle(self, event):
        """Return an action name, or None to stay put."""
        return None

    def update(self, inputs, dt):
        """One fixed simulation step. Interface scenes have nothing to advance."""

    def draw(self, surface, alpha):
        if self.opaque:
            surface.fill(BACKDROP)
            return
        veil = pygame.Surface(tuple(self.window), pygame.SRCALPHA)
        veil.fill(VEIL)
        surface.blit(veil, (0, 0))


class SceneStack:
    """The scenes currently open, innermost last."""

    def __init__(self, window):
        self.window = window
        self.manager = build_manager(window)
        self._scenes = []

    def __bool__(self):
        return bool(self._scenes)

    def __len__(self):
        return len(self._scenes)

    @property
    def top(self):
        return self._scenes[-1] if self._scenes else None

    @property
    def simulates(self):
        return bool(self._scenes) and self._scenes[-1].simulates

    def push(self, scene):
        """The new scene is built before the old one is torn down, so a scene
        that cannot lay itself out leaves the stack exactly as it found it."""
        try:
            scene.open()
        except Exception:
            scene.close()
            raise
        if self._scenes:
            self._scenes[-1].close()
        self._scenes.append(scene)
        self._sync_pointer()

    def pop(self):
        if not self._scenes:
            return
        self._scenes.pop().close()
        if self._scenes:
            self._scenes[-1].open()
        self._sync_pointer()

    def clear(self):
        while self._scenes:
            self.pop()

    def resize(self, size):
        """Rebuild the open scene against a new render size.

        `open()` is where a scene decides where everything goes, so reopening is
        the whole of re-laying-out -- there is no second layout path to keep in
        step with the first.
        """
        self.window = size
        self.manager.set_window_resolution(tuple(size))
        for scene in self._scenes:
            scene.window = size
        if not self._scenes:
            return
        top = self._scenes[-1]
        top.close()
        top.open()

    def _sync_pointer(self):
        """Gameplay draws its own crosshair with the system pointer hidden, so
        an interface scene has to ask for the real one back."""
        pygame.mouse.set_visible(bool(self._scenes) and not self._scenes[-1].simulates)

    def handle(self, event):
        self.manager.process_events(event)
        return self._scenes[-1].handle(event) if self._scenes else None

    def update(self, inputs, dt):
        """Only the top scene advances. Everything beneath it is paused, which
        is the definition rather than an implementation of pausing."""
        if self._scenes:
            self._scenes[-1].update(inputs, dt)

    def visible(self):
        """The scenes that have to be drawn, bottom first.

        Walking down until something opaque is reached is what lets pause show
        the live world beneath it instead of a screenshot taken when it opened.
        """
        showing = []
        for scene in reversed(self._scenes):
            showing.append(scene)
            if scene.opaque:
                break
        return list(reversed(showing))

    def draw(self, surface, alpha, dt):
        if not self._scenes:
            return
        for scene in self.visible():
            scene.draw(surface, alpha)
        self.manager.update(dt)
        self.manager.draw_ui(surface)
