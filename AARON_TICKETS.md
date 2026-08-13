# Aaron Tickets

Modernization backlog for the Top-Down Shooter. One ticket ≈ one PR.
Work top to bottom, except where a ticket says otherwise — AT10 and AT11 were
pulled ahead of AT4–AT9 so the risky refactors land with a net under them.

Tickets are identified `AT<N>` ("Aaron Ticket"). Use that ID as the prefix in
branch names, commit subjects, and PR titles — e.g. `AT2: dependency manifests`.
PRs target `dev`, not `master`.

**Template**

```
## AT<N> — <Title>

**Short description:** one or two sentences.

**Dependencies:** AT<N>, AT<N> — or `none`.

**Goals**
- [ ] concrete, checkable outcome
```

Status legend: `TODO` · `IN PROGRESS` · `DONE`

---

## AT1 — Move source into a `shooter/` package — DONE

**Short description:** Verbatim relocation of the eight root-level modules into a
proper package with snake_case names. No logic changes, no new dependencies, no
cleanup — imports and the entry point only, so the diff is reviewable as a pure move.

**Dependencies:** none

**Goals**
- [x] `git mv` each module so history follows the file
- [x] Layout: `shooter/{game,background}.py`, `shooter/entities/`, `shooter/ui/`, `shooter/systems/`
- [x] `__init__.py` in every package directory
- [x] Update import statements to the new paths (wildcard imports preserved as-is — AT9 removes them)
- [x] Add root `main.py` entry point; drop the bare `game_loop()` call from the bottom of `game.py`
- [x] `python main.py` from the repo root behaves exactly as `python ShooterGame.py` did

**Non-goals:** renaming classes/methods, touching bodies, fixing bugs, adding tooling.

---

## AT2 — Dependency + project manifests — DONE

**Short description:** Declare what the game needs to run so a fresh clone is one
`pip install` away instead of guesswork.

**Dependencies:** AT1

**Goals**
- [x] `requirements.txt` pinning `pygame-ce==2.5.8` (see resolution below)
- [x] `requirements-dev.txt` adding `ruff` + `pytest`; their config lands in AT10/AT11
- [x] `pyproject.toml` declaring the `shooter` package, `requires-python = ">=3.10"`, and a `shooter` console script
- [x] README: install + run instructions, controls table, screenshot, project layout
- [x] Verify a clean `python -m venv` install runs the game end to end

**Resolution — pygame vs pygame-ce:** pygame is **not** deprecated. `pygame-ce`
is a *fork* by pygame's former core developers, not an official successor — both
projects still exist. This was a choice between them, decided on maintenance
(checked 2026-08-11):

| | upstream `pygame` | `pygame-ce` |
|---|---|---|
| Latest release | 2.6.1, 2024-09-29 (~23 months) | 2.5.8, 2026-08-09 |
| Commits, last 12 months | 14 (0 in last 3 months) | 557 |
| Distinct authors, last 12 months | 3 | 35 |
| Highest CPython wheel | 3.13 | 3.14 |
| Installs on CPython 3.14 | no | yes |

`pip install pygame` fails outright on 3.14 — no wheel for any released version
and the source build errors. Staying upstream would have meant pinning to Python
3.13 or older on a package dormant since 2024.

Adopting it required **no source changes**: pygame-ce installs under the
`pygame` import name and is API-compatible, verified by running the original
unmodified 2017-era code against it in AT1. Ecosystem is following it too —
`pygame-gui` now requires `pygame-ce>=2.5.3` outright and `pytmx` ships a
`pygame-ce` extra.

Pinned exactly in `requirements.txt`; `pyproject.toml` carries the looser
`>=2.5.5,<3`.

**Constraint to hold:** pygame-ce is a *superset*. Treat the upstream pygame 2.6
API as the contract and avoid ce-only additions unless deliberate — hold that
line and reverting is a one-line change.

**Known limitation left for AT3:** the `shooter` console script and `main.py`
both still require the repo root as cwd, because assets resolve relative to the
working directory. Verified: launching from `/` dies on
`FileNotFoundError: No file 'Assets/Sounds/gunAudio.wav'`. Documented in the
README rather than silently shipped.

**Non-goals:** any change to game code. AT2 and AT2.1 touch only manifests,
README, and this file. QA confirmed the game still crashes on `Human.png` after
~7s exactly as it does on `master` — that is the correct outcome here, and it is
fixed in AT2.2.

---

## AT2.1 — Python toolchain and version pin — DONE

**Short description:** Pin the interpreter and adopt `uv` so contributors and CI
stop silently differing. Landed with AT2 rather than as its own PR — it edits
the same README install section, and splitting it would have guaranteed a
conflict for no review benefit.

**Dependencies:** AT2

**Goals**
- [x] `.python-version` pinning `3.14` (patch-floating, so security updates apply)
- [x] Un-ignore `.python-version` — the inherited pyenv-era `.gitignore` was silently swallowing it
- [x] README install path for macOS built on `uv`, with the pip flow kept for other platforms
- [x] Document why not Homebrew `python@3.x` and not `/usr/bin/python3`

**Why uv:** it manages interpreter *and* environment as standalone builds, so
nothing depends on Homebrew's rolling `python@3.x` formula — the usual cause of
"my venv broke after `brew upgrade`". Verified: `uv python install` fetched
CPython 3.14.7 in 2.3s (newer than the 3.14.4 Homebrew had), and the game ran a
full 380-frame exercise on it.

**Note on the version:** the 8-year-old code needed **no** changes to run on the
newest Python — it byte-compiles warning-free and runs on 3.14. There is no
interpreter upgrade ladder to climb. What was missing was the pin and the proof,
not modernization. `requires-python = ">=3.10"` is still an untested claim;
AT10's CI matrix is what makes it real.

**Follow-up — resolved in AT13.** `requirements.txt` and `pyproject.toml` both
declared the dependency, and `uv run` resolved from `pyproject.toml` rather than
the exact pin, so they could drift once a newer pygame-ce shipped. AT13
consolidates on `uv.lock` and deletes the requirements files.

---

## AT2.2 — Fix the `Human.png` crash — DONE

**Short description:** `PowerUps.Timer` loads `"Human.png"`, which is not in the
tree, so any power-up left on the field for ~400 frames (~7s) takes the whole
process down. Pulled out of AT4 and moved ahead of AT3 because it caps every QA
session at seven seconds and blocks meaningful review of the PRs that follow.

**Origin — dead on arrival since 2019-01-07.** `Human.png` was committed at the
repo root in `c8a5077` ("Initial"). Later the same day, `d5d1ac0` ("Updates")
reorganized every loose asset into `Assets/` subdirectories — `menu_1.jpg =>
Assets/Backgrounds/menu_1.jpg` and so on. In that single commit `Human.png` was
**deleted rather than moved**, and `PowerUps.py` was **added** carrying the line
that loads it. The code and the file's removal landed together, so this blink
has never worked, not once.

**Dependencies:** AT2

**Goals**
- [x] Remove the crash — the blink-before-expiry effect should not load a nonexistent file
- [x] Preserve the evident intent (flash the pickup as it nears expiry) rather than deleting the behaviour outright
- [x] Verify a power-up survives its full 1200-frame lifetime and expires cleanly
- [x] Verify picking one up still works

**Fix:** the blink swapped in a 10%-scaled `Human.png` — missing from the tree,
and a strange thing to blink a pickup to even if it were present. Replaced with
a transparent `Surface` of the same size, built once when the timer starts, so
the pickup visibly flashes out and back as intended. Net −2 lines.

**Not related to pygame-ce.** A missing file raises `FileNotFoundError` from
`pygame.image.load` on every pygame version ever released. This would have
crashed identically on the pygame 1.9 the game was written against.

**Non-goals:** everything else in AT4, the import-time asset loads in
`powerups.py`, and the `randint(2, 2)` power-up selection bug in AT5. This PR
fixes one crash and nothing else.

---

## AT3 — Asset path resolution + loader cache — DONE

**Short description:** Every asset path was a bare relative string like
`"Assets/cursor.png"`, so the game only ran with the repo root as cwd, and
`Human.update_anim` re-read and re-scaled a PNG from disk every frame.

**Dependencies:** AT1

**Goals**
- [x] `shooter/assets.py` resolving paths relative to the package, not cwd
- [x] Memoized `load_image` / `load_sound` so each file is decoded once
- [x] Preload animation frames into tuples; per-frame code indexes a list
- [x] All 28 hardcoded `"Assets/..."` strings routed through the resolver
- [x] Game launches correctly from an arbitrary working directory
- [x] Measure FPS before/after and record the delta in the PR

**Results:** uncapped throughput 297 → 360 FPS (+21%), steady-state image loads
1.00 → 0.00 per frame. Verified running from `/`, from `$HOME`, and via the
`shooter` console script from `/` — all of which previously died on
`FileNotFoundError`.

**Correction to this ticket's original claim:** it said both `update_anim`
methods hit the disk "every frame, per sprite". Only the player's did —
`Zombie.update_anim` is commented out in the main loop (AT5 re-enables it), so
the measured baseline was exactly 1.00 loads/frame regardless of zombie count.
The caching matters more once AT5 lands, since it removes the cliff entirely
rather than turning 1 load/frame into N.

**Bug found and fixed here — the game could not run on Linux.** `Human` and
`Zombie` built animation paths by concatenating the uppercase state name:
`"Assets/Player Animations/" + type + "/survivor-" + type + "_rifle_0.png"`
with `type` in `IDLE`/`MOVE`/`SHOOT`. On disk the directories are `Idle`,
`Move`, `Shoot` and the files are lowercase. **Zero of the constructed paths
matched exactly** — they resolved only because macOS APFS is case-insensitive.
On any case-sensitive filesystem the player animation raised `FileNotFoundError`
on frame one, which would also have failed AT10's CI on `ubuntu-latest`. The
frame tables now use the real on-disk names: 86/86 paths match exactly.

**Behaviour deliberately preserved:** the idle animation still shows frame 0
forever. `update_anim` increments `current_idle` but the original always
substituted `"0"` into the path, so idle has never animated. Left as-is here and
belongs with the other animation bugs in AT5.

**One dead-code fix:** `Zombie.update_anim` indexed its path off the `type`
parameter rather than `self.type`, so calling it with `"Null"` — its documented
no-op — would have built a `zombie_Null/` path. Unreachable today since the
method is never called, but it would have broken the moment AT5 enabled it.

---

## AT4 — Fix crashes and unsafe-shutdown paths — DONE

**Short description:** Live crash bugs and exit paths that only work by accident.

**Dependencies:** AT3

**Goals**
- [x] ~~`PowerUps.Timer` loads `"Human.png"`~~ — moved to AT2.2 and pulled ahead of AT3
- [x] `loadBackground.image_at`: `colorkey is -1` → `== -1`
- [x] Replace `pygame.quit(); quit()` with a real shutdown path
- [x] Move `pygame.mixer.init()` and the module-level `Sound(...)` loads out of import time
- [x] Move `PowerUps.og_image` off the class body

**Severity correction — goal 4 was a live crash, not tidiness.** The ticket
filed it as a style issue. It is not: `projectiles.py` called
`pygame.mixer.init()` at import, `game.py` imports `projectiles` at import, so
on any machine without a usable audio device the game died before
`pygame.init()` ever ran:

```
$ SDL_AUDIODRIVER=nonsense python main.py
pygame.error: Audio target 'nonsense' not available
```

Headless servers, containers with no ALSA/PulseAudio, and machines with audio in
a bad state all hit it. `pygame.init()` tolerates the same failure — it returns
`(4 succeeded, 1 failed)` and raises nothing — so deferring the load makes audio
genuinely optional. The game now runs **silently** instead of not at all.

**Sound loading is deferred, not optimised.** Measured 0.54 ms and 0.97 ms for
the two WAVs against a 16.7 ms frame budget, then ~0.0004 ms cached. The blink
of first-shot latency is 3–6% of one frame, once — so the pre-warm this ticket
originally proposed was dropped as unnecessary. `play()` returns early when
`pygame.mixer.get_init()` is falsy, which is what makes a missing device a
no-op rather than a relocated crash.

**Shutdown goes through the flag that was already there.** `game_is_running`
was declared at `game.py:40`, read at line 77, and never assigned `False` — a
dead flag. Both exit paths now set it, and a single `pygame.quit()` runs after
the loop. Better than the `sys.exit()` this ticket proposed: no `SystemExit`
thrown mid-frame, one teardown path, and `game_loop()` returns normally, which
let AT11's smoke test drop its exception-based escape.

**Consequence for the test suite.** `game_loop()` calling `pygame.quit()` tore
down the session display fixture and broke all 8 wave tests that ran after it.
`conftest` now re-initialises pygame per test when a previous one shut it down,
and `display` returns the *current* surface rather than a captured one.
Verified order-independent.

**`og_image` was deleted, not relocated.** `Timer` assigns `self.og_image`
before any read, so the class attribute was dead weight doing disk I/O at
import. Overlaps AT8's dead-code sweep.

---

## AT5 — Fix gameplay bugs — DONE

**Short description:** Behaviour that is plainly wrong rather than merely
stylistic. Each one changes how the game plays, so they land together.

**Dependencies:** AT4

**Goals**
- [x] Zombies never animate — `update_anim("MOVE")` commented out of the main loop, `"ATTACK"` likewise
- [x] `Human.rot_center` rotates without recentring, so the sprite drifts as it turns
- [x] `Shot.changeX/changeY` dead fields deleted
- [x] `collide_rect_ratio(.5)` no-op removed
- [x] `Cash.cash_add_remove` boundary arithmetic
- [x] `Zombie.remove_health` pays out once per zombie
- [x] Fullscreen toggle moved to `KEYDOWN`
- [ ] ~~Power-up selection and handlers~~ — split into AT5.1

**Five strict xfails flip to assertions here**, which is what they were for: the
three `Cash` boundary bugs, the double payout, and the idle animation. One
remains, owned by AT5.1.

**Animation was not a one-line uncomment.** Zombie frames differ per pose —
IDLE 120×111, MOVE 144×155, ATTACK 159×147 — while `__init__` forced 120×111 and
`self.rect` was never resized. Simply enabling animation would have drawn a
larger sprite anchored to a stale, smaller collision box. `update_anim` now
rebuilds the rect from the current frame while preserving `topleft`, which is
what `move_posistion` controls, so poses change without teleporting the zombie.

**Rotation now recentres.** Measured: 0 px centre drift across a full 360°
sweep, against a sprite that previously slid because the rect stayed fixed while
the rotated image grew from its top-left.

**Consequence worth knowing:** the player's rect is the bounding box of the
*rotated* sprite, so it grows from 156×103 to about 186×167 at 30°, and the
hitbox now varies with aim angle. That is the standard cost of axis-aligned
collision plus rotation, and it is still an improvement — previously the drawn
sprite and its collision box were simply desynchronised. A fixed hitbox
independent of the drawn frame would need a separate rect; worth doing only if
it actually feels wrong in play.

**On `collide_rect_ratio(.5)`:** removed as dead code rather than adopted. It
built a callable and discarded it, so the live behaviour has always been a
full-rect check; enabling a 50% hitbox would change difficulty, which is a design
choice and not a bug fix. One line to switch if the tighter box is wanted.

---

## AT5.1 — Power-up selection and handlers — DONE

**Short description:** `select_powerup` was pinned to Nuke by `randint(2, 2)`.
Restoring the full range needed the three empty handlers implemented first.

**Dependencies:** AT5

**Goals**
- [x] `random.randint(2, 2)` → the full `1..4` range
- [x] `MaxAmmo` — refill the reserve
- [x] `MaxHealth` — restore the player to full
- [x] `InstaKill` — 30 seconds of one-shot kills
- [x] Flip the last strict xfail, `test_every_kind_can_spawn`

**The suite now has no xfails left.** All six known bugs recorded during AT11
have been fixed and their tests rewritten as ordinary assertions.

**Pickups report, the game loop applies.** `update()` used to reach into
`zombie_group` to fire the Nuke itself. Adding MaxAmmo would have meant handing
it the gun, and InstaKill the buff timer — a pickup that knows every subsystem.
It now returns the kind collected, `EXPIRED`, or `None`, and `collect_powerup`
in `game.py` applies the effect. That also let `update()` drop its
`zombie_group` and `screen` parameters.

**InstaKill buffs the weapon rather than nerfing the zombies.** Aaron's call,
and the right one twice over: zombie health bars stay meaningful, and once kills
are worth points, zeroing health would silently change whatever that scoring is
based on. `Shot` now carries its own `damage`, set when it is fired, so bullets
already in flight keep the damage they were fired with. Grenades are deliberately
untouched — they already deal 75 and making area damage lethal on top of a 30
second buff is a balance decision, not a bug fix.

**30 seconds is 1800 frames** at the locked 60 FPS, named `INSTAKILL_FRAMES`.
AT12 converts it to seconds along with every other timer.

**A HUD indicator was not in the ticket but the feature is unusable without
one** — a timed buff with no feedback leaves the player guessing. Red
`INSTAKILL 27s` under the top HUD, counting down.

---

## AT6 — Coordinate system and magic numbers — DONE

**Short description:** The window is 1080×720, but constants from an abandoned
1920×1080 build were still scattered through the code.

**Dependencies:** AT5

**Goals**
- [x] `shooter/config.py` holding window, world, speeds, damage, rewards, wave scaling, timers, colours
- [x] Camera clamp derives from `WORLD` instead of an inlined `-5000 + window[…]`
- [x] Radar centre and scale derive from window and world
- [x] Spawn area named rather than inlined
- [x] No resolution literal survives outside `config.py`

**A real bug fixed: the radar was lying.** It was called with
`-camera_x + 960, -camera_y + 540` — half of 1920×1080 — so in a 1080×720 window
the player blip sat about 8 radar pixels off its true position. It now derives
from the actual window centre, and tests pin the mapping at the origin, the far
corner, and an arbitrary point.

**The radar scale was already right.** `/50` happens to equal
`WORLD // RADAR_SIZE` (5000 ÷ 100). It is derived now rather than coincidental.

---

## AT27 — Lift the game out of `game_loop` into a `Session` — DONE

**Short description:** `game_loop` is 297 lines holding 50 locals. Move the
world into an object so there is something to construct and something to throw
away.

**Dependencies:** AT26

**Goals**
- [x] `Session` owns the world: entities, camera, systems, HUD data
- [x] `game_loop` keeps only the shell: display, clock, fixed timestep, events
- [x] Rules arrive as a collaborator, so a campaign can replace freeplay later
- [x] No behaviour change; the existing suite is the guard

**297 lines and 50 locals became 89 and 13.** The world moved to
`shooter/session.py`.

**One dead line found on the way.** `human_anim` was assigned once per *frame*
before the event loop and then recomputed inside every simulation step, so the
frame-level assignment could never be read.

**One real fix.** The crosshair sampled the pointer later in the frame than the
aim did, so it could draw a frame away from where a bullet would go. Both take
one sample now.

**Review fixes (AT27.1).** `resize` took a window it mostly ignored: it set
`self.window` and re-centred the player, while the gun, the health bar and every
existing zombie kept the viewport they were built with. Production never noticed
because the shared `Viewport` mutates in place -- but a caller passing a fresh
one got zombies walking at the old screen centre, and the test written for it
checked only the two things that did update. It takes no window now, which is
what AT25's single shared viewport already meant.

`Session.aim` also started at the origin, so a click on the opening frame fired
at `atan2(0, 0)` -- straight right, wherever the pointer was. It samples the
pointer at construction, as the old loop did before it.

**`WINDOWRESIZED` handling went.** AT26 dropped `RESIZABLE`, so no resize event
is delivered any more; the surface is re-read where it can still change, at the
fullscreen toggle.

**Why this is the blocker.** Splash, main menu, start game, end game and restart
all need a game to *begin* and *stop*. Today the game is a function's local
scope: there is nothing to build, nothing to discard, and no way to have none of
it while a menu is up. Every other item on the roadmap waits behind this.

**The seam the loop already has.** `if screens: ... continue` is exactly the
boundary between shell and world -- the loop already knows how to run with the
world paused. Extraction follows that line rather than inventing one.

**Rules as a collaborator, not a class hierarchy.** `WaveSystem` already *is*
the freeplay rules: it decides what spawns and when. `Session` takes it as a
parameter rather than hard-coding it, which is the whole of the seam a campaign
mode needs. No `Mode` abstraction until there is a second implementation to
justify it.

**Keeping the save-game seam.** World state -- positions, health, wave count,
cash -- stays in plain attributes that never hold a `Surface`. That costs
nothing now and makes serialising a session additive later rather than a
rewrite. See AT30.

---

## AT28 — Load everything before play, never during — DONE

**Short description:** `load_image` is lazily cached, so the first zombie of a
kind or a background swap costs a hitch mid-game. Load up front instead.

**Dependencies:** AT27

**Goals**
- [x] Everything a session needs is loaded before the first frame
- [x] A test fails if the image cache grows during gameplay
- [x] The existing "Loading..." moment covers it; no progress bar yet

**The hitch was smaller than the ticket claimed, and the real cost was
elsewhere.** Measured before changing anything: the eight sprites read during
play cost 5ms in total, none of them a whole frame. What did cost was
`BackgroundSheet` calling `pygame.image.load` directly, outside the cache -- a
5000x5000 JPEG re-read for **180ms on every session**. Harmless today with one
game per process; a freeze on every "Start Game" once AT29 lands. Starting a
game now costs 0ms.

**The guard found a bug nobody was looking for.** `functools.cache` keys on the
call as written, so `load_image(path)` and `load_image(path, False)` were two
entries -- two reads of the same file and two copies of the same surface in
memory. `GunData` omits the flag, the manifest passes it, and the preload was
quietly loading a second copy of everything rather than preventing the lazy
read. Every loader normalises its arguments before the cache now.

**An explicit manifest, not a directory walk.** 14MB of the 19MB on disk is
backgrounds this mode never shows; loading them would trade a hitch for a slower
start. The cold-start test is what keeps the list honest -- it clears every
cache, preloads, plays, and fails naming anything that still reached disk.

**Measured.** First `Human()` costs 35ms, first `Zombie()` 42ms, one background
JPEG 162ms; 86 of 107 images end up cached. At 60Hz a 162ms hitch is ten lost
frames, and `MAX_FRAME_SECONDS` bounds the damage without hiding the stutter.

**The test is the point.** Run gameplay frames and assert
`load_image.cache_info().currsize` does not change. That is what stops lazy
loading creeping back as assets grow.

---

## AT29 — Gameplay becomes a scene — DONE

**Short description:** Generalise the AT21 screen stack so gameplay sits on it
like everything else, and `covers_game` becomes a plain `opaque`.

**Dependencies:** AT27

**Goals**
- [x] One stack holding splash, menu, gameplay and pause
- [x] `Session` is created when the gameplay scene is entered, dropped when it exits
- [x] Starting and ending a game become stack operations

**Two properties replaced the special cases.** `opaque` decides whether anything
below still needs drawing; `simulates` decides whether the fixed timestep
advances. Pausing is no longer a branch in the loop -- it is what happens when
the scene on top does not simulate.

**The frozen frame is gone.** Pause used to veil a screenshot taken the moment
it opened, which is why the crosshair had to be captured out of it. It is
transparent now, so the stack walks down and draws the live world underneath.
The crosshair moved to the shell, drawn only while the top scene is the one
being played -- it belongs to the application, like the frame counter, not to
the world.

**`push` closing the scene beneath it turned out to be right.** It exists so two
menus cannot both be live; gameplay has no widgets, so `open` and `close` are
deliberately empty and the session comes through untouched.

**A mechanical rename.** `Screen` became `Scene` and `ScreenStack` became
`SceneStack`, moving out of `ui/` to `shooter/scenes.py` -- a stack holding
gameplay is not part of the interface layer.

**We are most of the way there.** AT21 built a scene stack that deliberately
excluded the one scene that matters, which is why `Screen` has a `covers_game`
flag naming the thing it cannot hold. With gameplay on the stack that flag is
just opacity.

---

## AT30 — Splash, main menu, and ending a game — DONE

**Short description:** The flow: animated splash, main menu, start game, pause,
end game back to the menu.

**Dependencies:** AT28, AT29

**Goals**
- [x] An animated splash that hands over on its own and can be skipped
- [x] A main menu to start a game from
- [x] Pause gains END GAME, returning to the menu
- [x] Starting a second game owes nothing to the first

**The art was already in the repository.** `menu_1.jpg` has sat unused in
`Assets/Backgrounds` since 2019 -- a sunset, a shooter, a zombie and a
deliberately blank signpost, drawn for a menu that never got written. It is a
2:1 banner against a 3:2 window, so it is scaled to the width and sat on the
ground line with its own sky colour continued above. Cropping to fill would cut
the shooter off the left edge.

**Ending a game is a pop because the menu never left.** `START` pushes gameplay
*on top of* the main menu rather than replacing it, so END GAME drops the pause
screen and the game and finds the menu exactly where it was. Nothing has to be
rebuilt or remembered.

**Wall time is not the simulation clock.** An interface scene never gets
`update`, so a splash driven by it would sit on its first frame forever. Scenes
gained `tick(seconds)` -- real elapsed time, every frame, whatever is on top.
That also fixed something quietly wrong since AT21: `pygame_gui` was handed a
constant `1/60` from inside `draw`, so its own animations ran at the wrong rate
on any machine not managing exactly sixty frames.

**The splash ignores input for its first moment.** A key already held down when
the game launches should not blow straight through the title card.

---

---

## AT32 — Pixel-art menu theming — DONE

**Short description:** Rework the title art as 8-bit pixel art with a reduced
palette, and stop the interface font fighting it.

**Dependencies:** AT30

**Goals**
- [x] The menu and splash read as pixel art rather than a shrunken painting
- [x] A pixel title that needs no font file
- [x] Interface text stops being antialiased
- [x] Nothing expensive happens at load

**Palette, not pixel size.** Five directions were mocked up against the real
menu layout. Simply pixelating the painting reads as a low-resolution
photograph, because that is what it is -- the blocks stay soft. Naive
per-channel posterising gives hard edges but turns the teal-to-orange gradient
into a muddy grey step. Mapping every pixel to a *hand-picked* six-colour ramp
is what produces clean bands and flat silhouettes.

**Baked, not computed.** The mapping is a nearest-colour search per pixel --
about a second, which is nothing offline and exactly what AT28 spent a whole
ticket making sure never happens at startup. `tools/make_menu_art.py` writes
`menu_pixel.png` at 135x90, an eighth of the render surface, so the default
resolution gets whole square blocks. Building the backdrop went from ~200ms to
0.5ms as a side effect.

**Scaled with nearest-neighbour.** Interpolating pixel art is precisely the
thing that stops it looking like pixel art.

**A pixel font out of a vector one.** Text is rendered at a quarter size with
antialiasing off and blown up square, so there is no bitmap font to ship and the
letters keep their blocks at any resolution.

**The prose is left alone.** Turning antialiasing off across the theme made
`pygame_gui` warn about a font the confirmation dialog asks for through its HTML
parser, which the theme cannot reach by element id. The dialog body is prose
rather than a label, so it keeps the smooth font and the theme stays
warning-free -- a test asserts that, since `pygame_gui` warns where it might
have raised.

---

## AT33 — Bring the menu background to life — DONE

**Short description:** Animate the title art. Polish, deliberately separate from
the theming that established the look.

**Dependencies:** AT32

**Goals**
- [x] The sky moves without the art being redrawn
- [x] Something happens on a slow cycle, so the menu is not static while read
- [x] No per-frame cost worth measuring

**One picture, three times of day.** Dusk drifts to night, holds there, then
comes up through dawn and back, over 54 seconds. Nothing is redrawn -- the six
colours are replaced, so the sun becomes a moon and the sunset becomes a night
sky out of the same file.

**Quantised into steps, not interpolated per frame.** The cycle is cut into 108
steps, so the picture is rebuilt about twice a second rather than sixty times,
and every frame in between hands back the surface it already has. Measured on
the real menu: 0.46ms a frame and 20 rebuilds across ten seconds. One surface is
kept rather than a cache of many, because at full size each is three megabytes
and only ever one is on screen.

**The art and the palette have to agree.** `replace` silently misses a colour
that is not exactly right, and part of the picture would stop animating with
nothing to show for it. A test asserts the file contains only the palette being
cycled -- changing one channel of one colour fails it.

**Palette cycling is the period-correct technique.** The background is six
colours mapped from a painting; shifting *what those six colours are* over time
animates the whole sky at the cost of a palette swap, rather than moving
sprites. Cheap, and exactly how the era this is imitating did it.

**Candidates, cheapest first.** A slow warm-to-cool drift in the sky bands; the
sun creeping up or down a few pixels; stars fading in across the dark band as it
cools; grass along the bottom edge shifting by a pixel; the shooter's muzzle
flashing on a long random interval.

**`tick` already exists.** AT30 gave scenes real elapsed time every frame,
whatever is on top, which is precisely what this needs and why it is a small
ticket rather than a structural one.

**Watch the backdrop cache.** `backdrop()` is memoised per window size on the
assumption that it never changes. Anything that animates it has to own that
decision rather than quietly defeating it -- a test asserting the build is not
per-frame is already there.

---

## AT31 — A game can end — DONE

**Short description:** Nothing in the game can be won or lost. The player dies
and the world carries on without them. Everything about modes waits behind this.

**Dependencies:** AT29, AT30

**Goals**
- [x] A session knows whether it is still being played
- [x] Dying ends the game rather than leaving a corpse walking the zombies around
- [x] The rules can declare a win, which is the seam levels need
- [x] A result screen: what happened, retry, or back to the menu

**Losing beats winning.** A player at zero health has lost even if the rules
were about to be satisfied on the same step, so the session checks health first
and only then asks the mode.

**Reported once, not every frame.** An outcome stays true for every frame after
it happens, so the scene remembers that it has said so -- otherwise the shell
would be handed a result screen sixty times a second.

**The world stops because the result screen does not simulate**, not because
anything special was added. That is AT29's `simulates` doing its job; before
this the zombies kept closing in on a body.

**END GAME now pops down to the menu** rather than exactly two scenes, since a
game can be left from the pause screen or from a result screen and those are
different depths.

**Measured first.** `human.kill()` fires on death and nothing responds -- three
hundred steps later the zombies are still converging on a body and the wave
timer is still counting. There is no attribute anywhere that says a game is
over.

**Why this is its own ticket.** "Freeplay levels" and "campaign progress" both
mean *a level is completed*, and completion is a kind of ending. Building either
mode before a game can finish would mean inventing the concept twice.

**Losing is the session's business, winning is the rules'.** A player at zero
health is lost whatever mode is being played. Winning depends entirely on what
the mode considers finished, so it comes from the rules object AT27 left a slot
for -- and endless freeplay simply never declares one.

---

## AT34 — Freeplay levels — DONE

**Short description:** Turn endless waves into numbered levels with a target,
so freeplay has an arc rather than a difficulty curve that runs forever.

**Dependencies:** AT31

**Goals**
- [x] Numbered levels with a target rather than a curve that runs forever
- [x] Each level opens bigger and asks for more waves than the last
- [x] Winning offers the way onward; losing offers the way back
- [x] A level can be finished by playing it

**A level is a rules object.** `WaveSystem` already decides what spawns and
when; a level is the same thing with a finish line, declaring a win when its
target is met. That is what AT31's outcome seam is for, and it needed no change
to `Session` at all.

**A table, not a formula.** A formula is tempting and gives every level the same
shape. The point of authoring them is that the third can be a step up rather
than four per cent harder than the second.

**Freeplay does not run out.** Past the authored levels the hardest is played
again, rather than the game refusing to start. That is a decision the campaign
(AT35) will make differently -- it ends.

**Two guards, not one redundant one.** A finished level does nothing at all,
*and* the wave after the final one is never spawned. They look alike but hold
different moments: the first stops the timer churning, the second stops a wave
arriving in the instant between clearing the target and the result screen
appearing.

---

## AT37 — Items and the backpack — DONE

**Short description:** The primitive both halves need. Item definitions and a
container with a limited number of slots. No UI, nothing uses it yet.

**Dependencies:** none

**Goals**
- [x] An item definition: what it is, what kind, how many fit in a slot
- [x] A backpack of a fixed number of slots, upgradeable
- [x] Adding what will not fit takes what it can and says how much
- [x] Fully tested without a display

**Stacks fill before slots open, and empty in the other order.** Adding tops up
a part-used stack before starting a new one, so a pack never holds three
half-stacks of the same thing; removing drains the smallest first, so it empties
into whole stacks rather than a scattering of remainders that each cost a slot.

**A pack cannot shrink below what is in it**, because there is nowhere for the
overflow to go.

**One rule for what a slot count may be.** The constructor and `resize` were
disagreeing -- one clamped to the upper limit and the other did not -- which the
tests caught before anything used either.

**One primitive, two arcs.** A weapon is an item you equip; wood is an item you
stack; ammunition is an item that competes with both. Building this once means
weapons, loot and harvesting are all the same container afterwards.

**A partial add is the whole point.** `add` returns how many were actually
taken. A backpack that silently swallows everything makes looting a formality;
one that fills up makes it a decision, and gives a better backpack something to
be worth.

**No UI here.** This is the AT23 shape: the hard part is the rules, it has no
visual component, and bundling it with a screen would hide it behind UI review.

---

## AT38 — Weapons become data — TODO

**Short description:** Lift `GunData` out of `ui/hud.py` and make a weapon a
definition rather than a class. Behaviour preserved; still one gun.

**Dependencies:** AT37

**Goals**
- [ ] A weapon definition: clip, reserve, damage, reload, sprite, ammunition
- [ ] The current shotgun is one entry in a table
- [ ] The literal `60` stops being written eleven times

**A weapon model inside the HUD cannot grow.** `GunData` is in `ui/hud.py`,
which is where it was put when there was one gun and it was a readout. Weapon
variety starts by moving it.

**A live bug to fix on the way.** `reload_ammo` hardcodes `60` in five places
while the clip size is `config.CLIP_SIZE`. Changing that setting today gives a
gun that reloads to the wrong size, and `CLIP = config.CLIP_SIZE` is one of the
import-bound copies AT23's guard already refuses to let become a setting.

---

## AT39 — The knife, and equipping — TODO

**Short description:** Start with a knife. Hold one thing at a time and change
which.

**Dependencies:** AT38

**Goals**
- [ ] A melee weapon: no ammunition, short reach, no projectile
- [ ] The player starts with it and nothing else
- [ ] Equipping swaps what shooting does
- [ ] Switching by number key

**Melee is not a gun with range zero.** It has no projectile and no reload, so
it is the case that proves a weapon is a definition rather than a subclass of
the shotgun.

---

## AT40 — The armoury — TODO

**Short description:** SMG, shotgun, sniper, crossbow, each with their own
ammunition.

**Dependencies:** AT39

**Goals**
- [ ] Four weapons that feel different: rate, spread, damage, reload
- [ ] Rounds, shells and bolts as separate items in the backpack
- [ ] `gunAK47.png` finally referenced by something

**Ammunition is where the choice bites.** Per-weapon types mean a sniper and an
SMG compete for space rather than sharing a pool, which is what makes carrying
both a decision instead of an obvious yes.

---

## AT41 — The shop on the wall — TODO

**Short description:** Somewhere on the map you walk up to and buy from, not a
menu that appears between waves.

**Dependencies:** AT40, AT42

**Goals**
- [ ] A shop standing somewhere in the world
- [ ] Walking up to it offers to trade; a key opens it
- [ ] Coins buy a weapon and its ammunition
- [ ] Usable mid-wave, at the risk of standing still to do it

**A place rather than a moment.** The first plan was a between-wave menu, which
is a screen and nothing else. Putting it on the map makes buying a decision
about *where the player is* -- worth crossing the field for, dangerous with a
wave inbound -- and costs nothing extra once AT42 exists.

**Which is why AT42 now comes first.** A shop on the map is a world object like
any other; it should be that layer's first user rather than its own kind of
thing.

**Most of it was written in 2019 and never called.** `Cash.cash_add_remove`
already returns whether a purchase can be afforded, with a comment saying so,
and `Assets/Wall Items/gun_on_wall.png` had never been referenced by anything.

**The advertisement is gone.** The wave banner printed `[AMMO]  [HEALTH]  [GUN]`
for seven years for a shop nobody wrote. AT34 already stopped the player seeing
it -- `LevelRules.draw` never called the base version -- so it was dead code
promising a feature, and promising it in the wrong place. Deleted here rather
than left to be honoured by something else entirely.

---

## AT42 — Things in the world — TODO

**Short description:** A layer of objects that stay where they are. Nothing is
harvestable until something exists to harvest.

**Dependencies:** AT27

**Goals**
- [ ] World objects with a position, a footprint and health
- [ ] They occlude, collide, and survive the camera moving
- [ ] Standing near one offers an interaction; a key takes it
- [ ] Placed from a level definition rather than scattered at random

**This is the hidden cost in the resource half.** The world is a 5000x5000
background *image*. `Session` has groups for zombies, bullets, grenades and
power-ups -- everything that moves and nothing that stays. Trees, a downed plane
and a house are not more sprites, they are a layer the game has never had.

**It moved ahead of the shop.** Making the shop a thing on the map rather than a
menu means it needs this, so the weapon arc now waits one phase longer than the
coins-first ordering was chosen to avoid. Worth it: a shop you walk to is a
better game than a shop that appears, and the interaction built here is the same
one harvesting needs.

---

## AT43 — Harvesting — TODO

**Short description:** Chop a tree, strip the plane. Wood and metal into the
backpack.

**Dependencies:** AT37, AT42

**Goals**
- [ ] Hitting a world object with the right tool yields its resource
- [ ] An object is used up, and says so as it goes
- [ ] What will not fit in the backpack is left behind

---

## AT44 — Loot from the dead — TODO

**Short description:** Zombies drop what they were carrying.

**Dependencies:** AT37

**Goals**
- [ ] A drop table per zombie kind
- [ ] Dropped items are picked up by walking over them
- [ ] A full backpack leaves them on the ground rather than eating them

---

## AT45 — Crafting — TODO

**Short description:** Build a weapon from what you are carrying.

**Dependencies:** AT41, AT43

**Goals**
- [ ] Recipes: what it costs, what it makes
- [ ] Crafting consumes the parts and fails cleanly when short
- [ ] A cheaper path to a gun than buying one

---

## AT46 — The backpack screen — TODO

**Short description:** Look at what you are carrying, equip, and drop.

**Dependencies:** AT40, AT44

**Goals**
- [ ] A grid of slots on the AT22 layout
- [ ] Equip and drop from it
- [ ] It pauses the game, like every other screen on the stack

**Last on purpose, and cheap when it arrives.** AT22 built the grid, AT24 built
the widgets and the form, AT29 made a screen a scene. By the time this is
reached it is a layout over a container that already works.

---

## AT36 — Zombies that move like a crowd — DONE

**Short description:** They arrived in rank at one speed, converged until they
were a single sprite, and faced the same way whatever direction they walked.

**Dependencies:** AT27

**Goals**
- [x] Each zombie walks at its own pace
- [x] They push each other apart instead of stacking into one sprite
- [x] They turn to face whoever they are chasing
- [x] None of it changes how far a zombie can reach

**Facing must not become reach.** Rotating a sprite puts it on a bigger
surface: the footprint went from 144x155 to 201x205 on a forty-five degree
turn, which would have meant a zombie coming in diagonally touching the player
before one walking straight in. `rect` stays the upright footprint and only the
drawn image turns, with `image_offset` keeping the two centred -- measured
before and after rather than assumed.

**Rotation compounds if you let it.** The first version turned `self.image`,
which is already turned, so every call landed on a surface about forty per cent
bigger than the last. The game loop hid it because the animation re-chooses the
frame each step; a test that moved a zombie without animating it grew the
surface until the run stalled. Turning always starts from `self.upright` now.
The guard uses five turns rather than fifty, because a guard that exhausts
memory is worse than one that fails.

**Pushes are worked out before anything moves.** Applying them as the pairs are
walked would make the result depend on the order a sprite group happens to
iterate in, which is exactly the kind of thing that holds at sixty frames and
not at two hundred.

**Review fixes.** Pace quietly broke two things that had been settled
elsewhere. AT15 made the spawn ring a number of *seconds* rather than pixels, so
that the warning stays constant however the speed is tuned -- but the margin was
still read from the shared speed, giving the quickest zombie 2.54s of the 3.0s
the setting claims. And the shove that pulls zombies out of a pile used the
crowd's speed, so a stunned one was flung at 3.6 times its stunned pace, undoing
the stun exactly when it should read most clearly. Both now use the zombie's own
speed.

The test that was supposed to guard the first divided the margin by the same
shared constant it came from, so it could not have noticed. It is a per-pace
check now.

**Pace belongs to the zombie, not the config.** The stun timer used to restore
`config.ZOMBIE_SPEED`, which would have quietly re-paced every zombie that was
ever stunned. It restores that zombie's own walking speed now, and the tests
that compared against the shared constant compare against the zombie instead.

---

## AT35 — Campaign and persisted progress — DONE

**Short description:** Levels in sequence, checkpoints, and progress that
survives closing the game.

**Dependencies:** AT34

**Goals**
- [x] How far the player has reached survives closing the game
- [x] The menu offers to continue, and where from
- [x] The campaign ends rather than repeating its hardest level
- [x] A corrupt or stale save cannot stop the game starting

**Two problems, deliberately separated.** *Progress* -- which levels are
unlocked, the checkpoint reached -- is a handful of numbers, and AT23 already
had the pattern: validated JSON in the platform config directory written through
a temporary file. *Mid-game serialisation* -- exact zombie positions, ammunition,
where the wave had got to -- is a far bigger commitment and is deliberately not
here. AT27 kept the seam for it.

**A level is the checkpoint.** Reaching level four means level four can be
started again from its definition, which is a level number rather than a world.
That is the whole of what a checkpoint has to mean here, and it is why this
ticket needed no new machinery beyond a file with two keys in it.

**Nothing earned moves backwards.** Replaying an early level cannot take away a
level already reached, which is the one rule a progress store has to get right.

**A stale save is clamped, not refused.** A file claiming level nine of a
five-level game is not a reason to refuse to start; it is a reason to start at
five, and to say which keys were wrong.

**This supersedes AT34's last-level decision.** Freeplay repeated its hardest
level for ever because it had nowhere to end. A campaign ends, so finishing the
last level now says so. `level_number` still clamps, for a freeplay mode that
wants to keep going.

**Review fixes.** The save was called with nothing catching it, so a read-only
config directory or a full disk ended the game at the moment the player had just
won -- the rule `open_scene` and the fullscreen toggle already follow, not
applied here. It is suppressed now, and only for `OSError`: the session keeps
the progress, only the file is lost.

Two smaller ones in the validator. A level recorded twice was reported as a bad
key although every entry in it was valid, which would have blamed something that
was fine. And a `reached` too *high* was carefully clamped to the last level
while one too *low* for the levels already finished was accepted in silence,
offering a player who had beaten level three a CONTINUE that started them at
one; the two keys are reconciled now.

**The isolation had to be inherited, not copied.** `progress_path` is named from
the settings path, so whatever redirects one redirects the other -- but only
while it is reached through the module. Importing the function by name would
have quietly pointed the test suite at a real player's save file, so a fixture
now asserts the two stay together.

---

## AT26 — Resolution changes abort inside SDL — DONE

**Short description:** AT25 made `set_mode` something a player calls again from
the settings screen. With `SCALED | RESIZABLE` the second call aborts inside
SDL. Dropping `RESIZABLE` fixes it.

**Dependencies:** AT25

**Goals**
- [x] Find why CI segfaulted on `dev` from AT25 onward
- [x] Establish whether players are affected or only the dummy driver
- [x] Fix it, with a test that would have caught it

**Measured, not guessed.** Exit code 139 on Linux, 134 on macOS, both inside
`open_display`. Isolating the flags gave a clean answer:

| flags | 40 changes on a real driver |
|---|---|
| `SCALED \| RESIZABLE` | aborts, 4 runs in 5 |
| `SCALED` | survives, 5 in 5 |
| `RESIZABLE` | survives |
| neither | survives |

**Not a test artefact.** The first instinct was to blame SDL's dummy driver,
since that is what CI uses. Repeating the check against macOS's real `cocoa`
driver aborted 3 runs in 5, so this was a crash a player could hit by changing
resolution -- the tests only found it first.

**Why it went unnoticed.** It is a hard abort rather than a failed assertion,
and it needs a *second* `set_mode`, which nothing did before AT25. On macOS it
misses roughly five times in six, so it looked like flakiness; on Linux it is
reliable, which is why `dev` was red from AT25 onward while every PR run passed.

**What is lost.** The OS window can no longer be dragged to resize. `SCALED`
still letterboxes, the fullscreen toggle still works, and resolution is a
setting now -- which is what dragging was standing in for.

---

## AT25 — Changing resolution without restarting — DONE

**Short description:** Make `WINDOW` a live setting. Recreate the display and
re-lay-out against the new size, without touching game state.

**Dependencies:** AT24

**Goals**
- [x] One value for the render size, not a copy captured in twenty places
- [x] Changing the resolution setting takes effect immediately
- [x] No game state is disturbed: health, ammo, wave, and every world position survive
- [x] `WINDOW` reclassified from boot-only to live
- [x] The player stays centred and zombies keep walking at them

**Proved while paused.** The integration test pauses before changing resolution,
so the simulation is frozen and world positions can be compared for exact
equality. Resizing while the game runs would leave zombies legitimately walking,
and the assertion would have had to be a tolerance -- which would also have
passed if the resize had nudged something.

**Why there is nothing to save.** A zombie sits at `(2100, 3400)` in a 5000x5000
world; its health is a number and the wave counter is a number. None of that is
measured in pixels, so a resolution change cannot invalidate any of it. There is
no snapshot to take and no state to serialise -- the world stays in memory and
only the surface, the camera viewport and the layout are rebuilt. This is what
every modern engine does; the restart convention is a hangover from older
graphics APIs where recreating the device was genuinely painful.

**Why ours needs a restart today.** `window = config.WINDOW` is read once in
`game_loop` and then captured in about twenty places -- the screen stack, the
HUD, the player, the health bar, the gun, the camera clamps, the aim maths and
the background blit. Changing `config.WINDOW` afterwards reaches none of them.
It is the AT23 import-binding problem one level down: a local instead of a
module global.

**A shared viewport, not twenty resize methods.** Most of the readers already
ask for the size when they need it: `HealthBar`, `GunData` and `Zombie` all
index it at draw or step time. They are only stale because each holds its own
copy of a tuple. Passing one mutable `Viewport` instead makes them live for free
and leaves exactly two things to fix by hand.

**The two that genuinely compute once.** `Human` places its rect at the screen
centre in `__init__`, so it has to be re-centred. `HUD` bakes its piece
positions into `__init__` even though `update()` already receives the window,
so the arithmetic moves into `update()` and stops being a snapshot at all.

**Existing zombies are not cosmetic.** `move_toward_center` uses half the window
as the player's screen position, so a zombie holding a stale size walks toward a
point the player is no longer standing on. This is simulation behaviour, which
is why the shared viewport matters more than the HUD does.

**The loop reconciles rather than being told.** Settings writes `config.WINDOW`
on save, and the loop notices the display no longer matches and rebuilds. No
callback plumbing, and a change from anywhere is honoured.

**`VSYNC` stays boot-only.** It rides on the same `set_mode` call, so it looks
free -- but whether a driver honours a vsync change on an existing window varies
by platform, and that cannot be verified against the dummy driver used here.
Claiming it works live without testing it on real hardware would be a lie in a
settings screen.

**AT18 is not a prerequisite.** That ticket makes the HUD look right at any
aspect ratio; this one makes a resolution change work at all. They compose, and
neither blocks the other.

---

## AT15 — Zombies spawn around the world origin, not the player — DONE

**Short description:** `spawn_zombie` places zombies on a ring anchored at world
`(0, 0)` and sized `1920×1080` — a resolution the game does not use. Found while
doing AT6; **not** fixed there because it changes spawn distances, which is a
balance change rather than a constant rename.

**Dependencies:** AT6

**Goals**
- [x] Spawn just outside the current viewport rather than around the origin
- [x] Retire `config.SPAWN_AREA` once the ring is camera-relative

**The player is the centre of the visible world.** A sprite is drawn at
`world + camera`, so the world rectangle on screen is `(-camera, window)` and
the player -- always drawn at screen centre -- stands at its middle.
`viewport.visible_world` says that once, and the spawn ring is built around it.

**The margin is time, not pixels.** A wave starts `SPAWN_LEAD_SECONDS` of
travel outside the view -- three seconds at the default speed, about 1080px --
so the player sees it coming instead of meeting it at the screen edge. Deriving
it from `ZOMBIE_SPEED` means a faster zombie starts further out and the warning
stays the same however the tunables are set, and a floor keeps it clear of the
sprite so nothing ever appears half on screen. Computed when a zombie spawns
rather than bound at import, because `ZOMBIE_SPEED` is a setting.

`SPAWN_LEAD_SECONDS` is itself a `new entities` setting on the dev screen, so
the feel can be dialled in without a code change.

**Not clamped to the world.** Standing in a corner, the ring extends past the
map edge and zombies start slightly outside it, then walk in. The original did
the same -- it spawned at `-1` -- and clamping would trade an invisible
out-of-bounds spawn for a visible one appearing on screen.

**Two dead functions removed while here:** `game.reset_zombie_pos` and
`WaveSystem.wave_gui`, neither called from anywhere. The first would otherwise
have grown a parameter it never receives.

**Why it matters.** The world is 5000×5000 and the camera clamps to
`-(5000 - window)`, so the player can stand at world x ≈ 4460 while zombies are
still being placed within x ∈ [0, 1920]. They do converge — `move_toward_center`
homes on the player wherever they are — but they can start thousands of pixels
away, so wave difficulty varies with where the player happens to be standing.
Not fatal, which is why it is its own ticket rather than a hotfix.

---

## AT7 — Class attributes used as mutable instance state — DONE

**Short description:** Nearly every class declared its mutable state on the
class body. It worked only because `+=` on an int rebinds to the instance.

**Dependencies:** AT6

**Goals**
- [x] Move all mutable state into `__init__` across all 13 classes
- [x] Drop the dead `HealthBar.lives` and `Human.player_cash`
- [x] `Zombie.zombie_speed` resets from `config`, not a class attribute

**52 class attributes → 4**, and the four that remain are genuine read-only
constants: `GunData.CLIP`, `GunData.RESERVE`, `Shot.SPEED`, `Shot.STEPS`. The
last two were `bullet_speed` and `continuous` — renamed to caps so they stop
reading like state.

**The old isolation tests passed by accident.** Demonstrated before touching
anything: after `a.increase_cash(50)`, `'cash_amount' in vars(a)` is `True` but
`vars(b)` is empty — `b` was reading the class attribute and merely looked
correct. The five "two instances do not share" tests written in AT11 could not
have caught a genuine sharing bug involving a list or a dict.

**A structural guard replaces the accident.** `test_no_class_body_still_declares
_mutable_state` walks the AST of every module and fails on any non-`ALL_CAPS`
assignment in a class body. Mutation-tested: reintroducing `cash_amount = 0` on
`Cash` turns it red.

---

## AT8 — Delete dead code — DONE

**Short description:** Eight years of commented-out experiments, plus the lint
rules that were suppressed because of them.

**Dependencies:** AT5

**Goals**
- [x] `Shop_Gui` (never instantiated), commented-out `Zombies_Killed`, the `Clock` stub
- [x] `from CarePackage import PackageSystem` (module does not exist)
- [x] Commented-out `Shot.update`, assorted `#pygame.draw.rect` leftovers
- [x] `width` / `height` / `human_X` / `human_Y` / `BLACK` / `WHITE` globals
- [x] `gun_data.reloading` renders from a data class — blit moved to the caller
- [ ] ~~Unused asset files~~ — kept deliberately, see below

**Four rule codes come off the ignore list here:** `F841`, `B007`, `SIM102`,
`SIM103`. The remaining 154 suppressed violations are all AT9.

**`Clock` was never code.** It sat inside a triple-quoted string — text, not a
class, so nothing ever referenced it and nothing ever would have.

**`reloading()` was drawing twice.** It called `self.update(screen)` while
`game_loop` already blits the ammo HUD every frame, so during a reload the
counter was rendered twice per frame. The blit is gone and the method no longer
takes a screen at all, which is the point — a data class should not draw.

**Assets deliberately not deleted.** Seven files (2.3 MB) are unreferenced, but
five of them are the roadmap rather than rubbish: `menu_1.jpg`, `menu.png` and
`ZombieShooter_Bck.jpg` are exactly what the planned splash and menu screens
need, and `gunAK47.png` with `gun_on_wall.png` are the weapon shop that
`Shop_Gui` was a stub for. Deleting them would work against AT14's stated
direction. Only `blackBox.jpg` (0 bytes) and `gun audio.mp3` (superseded by
`gunAudio.wav`) are genuinely junk, and together they are 10 KB — not worth a
decision. `Shop_Gui` itself is gone because it was an empty sprite subclass; the
art it implied is kept.

---

## AT9 — PEP 8 naming and import hygiene — DONE

**Short description:** Mechanical rename pass. Large diff, near-zero risk, and
the last thing standing between us and a linter with nothing suppressed.

**Dependencies:** AT8

**Goals**
- [x] Classes to PascalCase
- [x] Methods and attributes to snake_case
- [x] `posistion` typo fixed throughout
- [x] Wildcard imports replaced with explicit ones
- [x] `ruff format` across the tree, and enforced in CI

**The ignore list is gone.** `pyproject.toml` no longer has one. Every rule in
`E, W, F, B, C4, SIM, UP, N, RUF` is enforced, plus `ruff format --check` in CI.
167 suppressed violations at the start of AT8, zero now.

**Landed as two commits on purpose.** 352 renames first, then the 703-line
`ruff format` sweep. Combining them would have made the rename unreadable; split,
the first commit is reviewable and the second is "the formatter did it".

**The sweep got one thing wrong and the tests caught it.** `\bMaxAmmo\b` matched
inside `"Power Ups/MaxAmmo.png"` — `/` and `.` are word boundaries — so three
asset paths were renamed along with the methods they shared a name with. Fixed,
then every referenced asset path was audited against disk: 104 referenced, all
present.

**Two wildcard imports were pure dead weight.** `zombie.py` star-imported all of
`hud` and used nothing from it; `waves.py` did the same.

**`ruff format` also finished off `E501`.** Three lines it could not fix were
comments: one was dead commented-out code AT8 missed, one was an overlong
trailing comment, one needed moving above its loop.

---

## AT10 — Lint and CI — DONE

**Short description:** Get a gate in place *before* the large-diff refactors,
not after. Reordered ahead of AT4–AT9 by agreement: we found two real bugs by
hand (the `Human.png` crash, the Linux case mismatch) and both were trivially
catchable, while AT7 rewires state on every class and AT9 renames across every
file. Those should not land without a net.

**Dependencies:** AT2

**Goals**
- [x] `ruff` config in `pyproject.toml`; repo passes `ruff check` clean
- [x] `.github/workflows/ci.yml` running lint + smoke checks on push and PR
- [x] CI matrix over Python versions (narrowed in AT10.1 — see below)
- [x] CI runs on `ubuntu-latest` — a genuinely case-sensitive filesystem

**Deferred, with reasons:**
- `ruff format` — reformatting every file would touch every line and make the
  AT4–AT9 diffs unreviewable. Belongs with AT9, which is already a mass rename.
- `mypy` / type hints — the annotations would collide with AT7's state rework
  and AT9's renames. Cheaper once names stop moving.
- Pre-commit hooks — CI is the gate that matters; hooks are convenience.

**Rules deferred, not waived.** The `ignore` list in `pyproject.toml` names the
ticket that owns each code, so the gate tightens as they land: naming and
wildcard imports and line length are AT9; dead code and collapsible branches are
AT8. 19 violations were auto-fixed here; everything else is either fixed or
explicitly owned.

**Matrix narrowed in AT10.1.** The original 3.10–3.14 sweep never produced
independent signal: across 8 runs all five jobs agreed every time, and the code
has no version-conditional branches at all — no `sys.version_info`, no guarded
imports. It now runs two jobs: **3.14**, the version pinned in
`.python-version`, which gates merges; and **3.15**, the next release, as a
non-blocking canary via `continue-on-error`.

**Open consequence — decided in AT13.** `requires-python = ">=3.10"` became an
untested claim once the matrix narrowed. AT13 narrows it to `>=3.14` so the
declaration matches both `.python-version` and what CI gates on.

**On the asset guard:** the first version used `os.path.exists`, which is
case-insensitive on macOS and so would only have caught an AT3-style regression
once it reached CI. Rewritten to compare against an exact set built from
`os.walk`, so it fails on any platform. Verified both ways — passes on current
code, exits 1 when fed the old uppercase paths.

---

## AT11 — Tests for game logic — DONE

**Short description:** There were zero tests. The ammo/reload state machine,
cash, wave scaling, damage math, and the power-up lifetime are pure logic and
testable headlessly under `SDL_VIDEODRIVER=dummy`.

**Dependencies:** AT10

**Goals**
- [x] `pytest` + a conftest that forces the dummy SDL video/audio drivers
- [x] Cover `gun_data` reload transitions (empty clip, partial clip, no reserve, manual reload)
- [x] Cover `Cash` add/remove including the boundary cases AT5 fixes
- [x] Cover `Wave_System` spawn counts and `5 + wave²` scaling
- [x] Cover `Human` / `Zombie` damage, death, and regen
- [x] A smoke test that constructs the game and steps N frames without raising

**63 tests: 57 passing, 6 `xfail(strict=True)`.** CI now runs the suite across
Python 3.10–3.14 instead of the inline smoke scripts AT10 used as a placeholder.

**Tests pin current behaviour, not intended behaviour.** That is the point — the
suite exists to stop AT4–AT9 from changing semantics by accident. Known bugs are
recorded as strict xfails instead, so when AT5 fixes them the suite fails until
the tests are rewritten as ordinary assertions. Four are marked: `Cash` refusing
a zero-balance transaction, refusing to spend the balance exactly, allowing an
overspend into negative, and the idle animation being pinned to frame 0.

**Mutation-tested rather than assumed.** A suite that cannot fail is worthless,
so each landed fix was reverted in turn to confirm something goes red:

| reverted | caught by |
|---|---|
| AT2.2 `Human.png` blink | 2 power-up tests |
| AT3 uppercase animation paths | case-sensitivity test |
| reload arithmetic (`-= 60` → `-= 30`) | 2 gun tests |
| wave scaling (`5 + n²` → `5 + n`) | 4 wave tests |

The `Human.png` case matters most: that crash shipped for seven years, and a
test stepping a power-up through its 1200-frame life would have caught it the
day it was written.

**Class-attribute state is covered deliberately.** Several tests assert that two
instances do not share health, ammo, cash, or wave progress. Those currently
pass by accident — `+=` on an int rebinds to the instance — and they are exactly
the invariant AT7 must preserve when it moves that state into `__init__`.

**Convention: one signal per known bug.** A bug is recorded *only* as a strict
xfail describing the intended behaviour, never as a plain assertion of the
broken outcome. Two tests for one bug means AT5 gets a clean XPASS on one and a
confusing hard failure on the other. Review of this PR caught three departures
from that rule, all now fixed.

**Tests must not depend on bugs they do not own.** The power-up tests originally
relied on `PowerUp_Selection` being hardcoded to `randint(2, 2)`. Simulating
AT5's fix made them fail on 3 of 6 runs — the suite built to protect AT5 would
have broken *on* AT5. Power-ups are now constructed through a `make_powerup`
factory that pins the kind via a scoped `MonkeyPatch.context()`, and the
lifetime, blink and pickup tests are parametrised over all four kinds, so AT5's
fix is exercised before it lands.

---

## AT13 — Single source of truth for dependencies — DONE

**Short description:** The dependency was declared three times and `uv run`
read the wrong one. Consolidate on `pyproject.toml` + `uv.lock` and delete the
requirements files.

**Dependencies:** AT2.1, AT10.1

**Goals**
- [x] Dev tooling moves to a PEP 735 `[dependency-groups]` entry
- [x] `uv.lock` committed as the exact, reproducible resolution
- [x] `requirements.txt` and `requirements-dev.txt` deleted
- [x] CI switches to `uv sync --locked`
- [x] README install collapses to a single `uv sync`
- [x] Decide `requires-python`

**The drift this removes.** `requirements.txt` pinned `pygame-ce==2.5.8` while
`pyproject.toml` declared `>=2.5.5,<3`, and `uv run` resolved from the latter.
Identical today, divergent the day 2.5.9 ships. One source now, and
`uv sync --locked` in CI additionally fails if the lock falls out of step with
`pyproject.toml` — verified by editing the range without re-locking.

**`requires-python` narrowed `>=3.10` → `>=3.14`.** It had gone back to being an
untested claim after AT10.1 cut the matrix to 3.14 + 3.15. Narrowing makes the
declaration match `.python-version` and the CI gate. Little is lost: `uv sync`
fetches 3.14 regardless of the system Python, so uv users are unaffected;
only a non-uv `pip install -e .` on 3.10–3.13 is refused. One line to widen
again if we decide to support and test those.

**No version changed.** The lock resolves to exactly what the deleted files
pinned: pygame-ce 2.5.8, pytest 9.1.1, ruff 0.16.2.

**Verified from a clean `git archive`:** `uv sync` alone fetches CPython 3.14.7,
creates the venv, installs from the lock, and editable-installs the project —
63 tests pass, ruff clean, the game runs, and the `shooter` console script runs
from `/`.

---

## AT14 — Pause, and the seam for a screen system — DONE

**Short description:** `Escape` pauses and resumes. Deliberately small, but
shaped so the eventual splash → menu → game → pause-menu flow grows out of it
instead of replacing it.

**Dependencies:** AT5

**Goals**
- [x] `Escape` toggles pause; the world stops, the frame stays on screen behind an overlay
- [x] Movement, zombies, projectiles, and every timer freeze while paused
- [x] `Escape` resumes
- [x] Rebind quit off `P`

**Where this is going.** The intended end state is: animated splash → main menu
(*start game*) → playing → pause menu (*resume*, *settings*, *end game*) → back
to the menu. Pause is the first screen that is not "playing", so it is the
right place to introduce the seam — but only the seam.

**The seam is a named state, not a boolean.** `state = PLAYING | PAUSED` extends
to `SPLASH | MENU | PLAYING | PAUSED | GAME_OVER` by adding names; a `paused =
True/False` flag would have to be torn out. That single choice is the whole
forward-compatibility story for this ticket.

**What is deliberately *not* built here, and why.** A real screen system needs
two refactors this ticket must not attempt:

1. **Update and draw are interleaved.** `grenades.update(cameraX, cameraY,
   screen, explosions)` takes the screen; `zombie.health_bar(screen)` draws from
   inside the zombie update loop. Menus need to draw without updating, which
   means untangling every one of those call sites.
2. **All game state is local to `game_loop`.** Roughly thirty locals — camera,
   sprite groups, HUD, wave system. A menu that can *start* a game needs that
   state constructed and discarded on demand, i.e. lifted into an object.
   Overlaps AT7.

Pause dodges both by snapshotting the frame on entry and blitting the snapshot
under the overlay, so nothing needs to redraw while paused. That is a real
technique, not a stopgap, and it stays useful once screens exist.

**Interaction with AT12.** Every timer is a frame counter today — `Wave_Timer`,
`stun_timer`, `reload_time`, `PowerUps.timer_count` — so skipping the update
block freezes them correctly and pause works naturally. Once AT12 moves to
delta-time, pause must not accumulate `dt` across the paused span or everything
jumps on resume. Whoever does AT12 owns that.

**Quit moves off `P`.** `P` currently quits immediately with no confirmation,
which is the key most players press expecting pause. With `Escape` taken by
pause, quitting belongs in the pause menu; until that exists, `P` is at least a
surprise worth removing.

---

## AT12 — Frame-rate independence — DONE

**Short description:** Every speed and timer was counted in frames against a
locked 60 FPS, so anything that dropped frames played in slow motion.

**Dependencies:** AT7

**Goals**
- [x] Thread `dt` from `clock.tick` through every entity update
- [x] Speeds become pixels per second, durations become seconds
- [x] Behaviour verified at 30, 60 and 144 FPS

**Measured in the real loop, not just unit-tested.** Driving `game_loop` with a
fake clock at three rates, standing still with identical spawns:

| | 30 FPS | 60 FPS | 144 FPS |
|---|---|---|---|
| health after 2s | 87.30 | 87.00 | 86.69 |
| camera after 2s holding D | −1190 | −1200 | −1206 |

Within about 1% across a 4.8× spread; the residue is frame quantisation.

**Before the last fix those same numbers were 100 / 0 / 0 and −1190 / −990 /
−381** — the player survived at 30 FPS and died before two seconds at 144.

**Three of my own edits silently did nothing.** `ruff format` had already
reflowed the code my replacements were matching on, and because those particular
replacements had no assertion they failed quietly:
`Shot.update`'s body, its off-screen bound, and — the one that mattered — the
zombie damage call, which `ruff` had wrapped across three lines so
`config.ZOMBIE_DAMAGE` never gained its `* dt`. Damage then scaled with frame
count. Caught by driving the real loop rather than trusting the unit tests, all
of which passed throughout.

**Bullets sub-step by distance now.** The old loop ran a fixed number of 14px
steps per frame; it now derives the step count from `SPEED * dt`, so the
anti-tunnelling property holds at any frame rate instead of only at 60.

**Grenades fly for a duration.** `x_counter` / `y_counter` counted frames along
each axis; a grenade now travels for `distance / GRENADE_SPEED` seconds and then
fuses for `GRENADE_FUSE` seconds.

**`MAX_FRAME_SECONDS` caps `dt` at 0.1s** so a stalled frame cannot teleport
anything across the map, and the paused branch resets `dt` every frame — the
obligation AT14 recorded. Resuming cannot bank the paused duration.

**Animations advance on their own clock.** `ANIMATION_FPS = 60` reproduces the
previous one-frame-per-tick behaviour exactly at 60 FPS while staying correct
elsewhere.

---

## AT16 — Fixed timestep — DONE

**Short description:** Replace AT12's variable delta time with a fixed-step
accumulator, so the simulation advances in constant increments no matter how
fast the machine draws.

**Dependencies:** AT12

**Goals**
- [x] Accumulator loop: simulate in constant `SIM_DT` steps
- [x] Keep the frame-time clamp as the spiral-of-death guard
- [x] Determinism: identical state after an equal number of steps at any frame rate
- [x] Interpolate entities between steps — completed in AT19
- [ ] Retire the bespoke bullet sub-stepping — deferred, see below

**Determinism achieved, which AT12 could not give.** Byte-identical state hashes
after 200 simulation steps at 30, 60, 90, 144, 200 and 300 FPS. AT12's best was
87.30 / 87.00 / 86.69 — close, never equal.

**Groundwork first: simulation and drawing were interleaved.** `health_bar` drew
from inside the zombie update loop, `wave_control` both advanced the timer and
drew its banner, and both throwables took a `screen` they never used. A fixed
step cannot exist until simulating and drawing are separable, so that landed as
its own commit.

**Two real bugs surfaced, both invisible to the unit tests.**

The first was a duplicated movement block: the original per-frame camera update
was left in place alongside the new per-step one, so the camera moved twice.
Arithmetic confirmed it exactly — at 144 FPS, 144 frames × 10px plus 59 steps ×
10px is the 2030px that was measured.

The second was subtler and is the interesting one. `human.rot_center` was in the
render pass, but it resizes `human.rect`, which collision reads. More frames per
step meant more compounding rotations, a larger hitbox and more damage taken —
health diverged to 97.55 at 144 FPS and 93.05 at 200 while staying 100 at 60.
**Rotation is not purely cosmetic here**, so it now runs once per step.

**Interpolation is deliberately partial, and that is a constraint not a
shortcut.** Only the camera is interpolated. Interpolating *some* things is
worse than interpolating none — the ground would scroll smoothly while zombies
stepped at 60 Hz. Because `FPS == SIM_HZ`, the accumulator remainder is
approximately zero and `alpha` is approximately zero, so interpolation is
currently a no-op regardless. It becomes necessary the moment the render cap
rises above `SIM_HZ`, which is what AT19 covers, and `config.py` records the
constraint.

**Bullet sub-stepping stays for now.** The accumulator bounds how much time a
step covers, but a single 1/60s step still moves a bullet 150px — far enough to
tunnel past a zombie. The sub-stepping is doing a different job than the
accumulator and cannot simply be deleted; revisit when physics arrives and owns
continuous collision.

---

## AT19 — Interpolate entities between simulation steps — DONE

**Short description:** Finish what AT16 started. Every drawn entity now keeps a
previous world position, so rendering can draw between steps — which is what
lets the renderer run faster than the simulation.

**Dependencies:** AT16

**Goals**
- [x] Zombies, bullets, throwables, detonations and power-ups keep a previous world position
- [x] Render positions computed as `previous + (current - previous) * alpha`
- [x] `FPS` decoupled from `SIM_HZ`; the constraint note in `config.py` is gone
- [x] Confirm motion is smooth above 60 Hz with the simulation still at 60 Hz

**Measured.** Rendering at 144 Hz against a 60 Hz simulation draws the camera at
**142 distinct positions per second** rather than 60, with `alpha` ranging up to
0.917. At 60 Hz `alpha` stays 0 — there is no remainder to interpolate, exactly
as expected.

**Drawing never touches `rect`.** That is the rule AT16 paid for: `rect` is
simulation state that collision reads, and rendering that mutates it makes the
hitbox frame-rate dependent. Entities expose `draw_position()` and a
`blit_group` helper blits there, so `rect` stays authoritative. A test asserts
every mover's `rect` is unchanged after a full interpolated draw.

**`PowerUps` had no world position at all.** It accumulated camera deltas
straight into `rect`, so there was nothing to interpolate *from*. It now holds a
world position like every other entity and derives `rect` from it, which also
removes an inconsistency rather than just enabling interpolation.

**A mismatch the decoupling exposed.** Thirteen simulation methods defaulted to
`dt=1 / config.FPS`. Once `FPS` became the *render* cap that default was simply
wrong, and it was silently correct only while the two rates were equal. They now
default to `config.SIM_DT`, and `config.FPS` appears in exactly two places, both
capping frames.

**Render cap is 240, not uncapped.** `FPS = 0` spins a core flat out. Vsync is a
display concern and belongs with AT17.
---

## AT17 — Resizable window via SCALED — DONE

**Short description:** Let players size the window freely, with the game keeping
a fixed logical resolution.

**Dependencies:** AT12

**Goals**
- [x] `set_mode(WINDOW, pygame.SCALED | pygame.RESIZABLE, vsync=1)`
- [x] Fullscreen actually fills the display instead of re-opening at 1080×720
- [x] Handle `WINDOWRESIZED`, not the legacy `VIDEORESIZE`
- [x] Verify the documented resize-smaller limitation
- [ ] Confirm mouse aiming still lands correctly — needs manual QA, see below

**Measured, on a real display.** Without SCALED, going fullscreen changes the
render surface itself to 1147×716, which moves every fixed HUD offset. With
SCALED the surface stays 1080×720 while the window grows to 1800×1130. A frame
captured in fullscreen is 1080×720 with the HUD exactly where it belongs.

**Fullscreen was re-opening the window.** The old toggle called
`set_mode(FULLSCREEN)`, which recreated the window at the same 1080×720 — so
"fullscreen" never filled a modern display. `toggle_fullscreen()` does, and a
test asserts `set_mode` is called exactly once for the whole session.

**A crash this introduced, caught by the tests.** `toggle_fullscreen()` raises
`pygame.error: That operation is not supported` on SDL's dummy driver. The old
`set_mode` path never did, so pressing `\` could have taken the game down on
some drivers. Wrapped in `contextlib.suppress(pygame.error)` — a keypress must
not be able to kill the process.

**Mouse scaling is documented but unverified.** pygame states *"mouse events are
scaled for you"*, and aiming here is raw pointer arithmetic so it matters. I
could not verify it programmatically: `set_pos` round-trips do not prove
anything without real pointer input, and SCALED cannot engage headlessly at all.
**Needs a human to play in fullscreen and confirm the crosshair still tracks.**

**CI cannot test the scaling itself.** SDL's dummy driver has no renderer, so
SCALED silently degrades and warns "no fast renderer available" on every
`set_mode`. The tests pin what is observable headlessly — the flags requested,
that `set_mode` runs once, that the logical surface never changes size — and the
warning is filtered by exact message in `pyproject.toml`.

**vsync is on.** It caps rendering at the display refresh, observed at 120 FPS
on this machine against the 240 config cap. AT19 made that safe: rendering and
simulation are independent, so a vsync cap cannot slow the game down.

**The known limitation stands.** pygame issue #3709 — a SCALED window cannot be
resized below its design size — is unresolved upstream. 1080×720 is therefore a
floor, not a default. Acceptable, but it is why AT18's anchoring matters: the
window can only grow, and a stretched HUD is the thing anchoring fixes.

**Also corrected the README controls table**, which still listed `P` as quit.
That has not been true since AT14 moved quitting behind the pause screen.

---

## AT18 — Adaptive HUD via anchors — DONE

**Short description:** Scaling is not layout. Reposition HUD elements relative
to window edges instead of stretching a fixed-resolution image.

**Dependencies:** AT17, AT21 (which owns adopting `pygame_gui`)

**Goals**
- [x] Rebuild the HUD with anchors
- [x] Replace the hand-tuned absolute offsets throughout `ui/hud.py`
- [x] Fix the wave banner, currently fully absolute at `(300, 210, 500, 100)`
- [x] Radar, ammo, health and cash all track their nearest corner

**The premise was half right.** Measured before changing anything: six of the
eight HUD positions already tracked their corner, because
`(window[0] - 263, window[1] - 162)` *is* an anchor, just written as a magic
number coupled to the art being 223x121. Only three things were genuinely
absolute and genuinely broken -- the health meter at `(480, 10)`, the cash
readout at `(400, 7)`, and the wave banner. Those are the three the tests catch;
the rest is the same layout said properly.

**Not `pygame_gui` anchors.** The HUD is drawn with direct blits inside the game
render path, and it changes every frame -- a health bar that is a `UIElement`
would be rebuilt constantly and drawn by the manager, out of order with the
world. `anchor.place` copies the model the ticket asked for, as arithmetic
returning rectangles, exactly like the AT22 grid.

**Readouts belong to panels, not to the window.** The numbers are drawn *on*
the HUD art, so they take their position from the panel's rectangle. The number
and the artwork under it can no longer drift apart, which is a stronger
guarantee than both happening to track the same corner.

**Locked at the tuned resolution.** A test asserts every element lands on the
exact pixel the old formulas gave at 1080x720. Anchoring is meant to change what
happens at *other* sizes, and nothing else.

**Why anchors.** `pygame_gui` positions elements with anchors such as
`{'right': 'right', 'bottom': 'bottom'}`, which keeps an element's size while
tracking a container edge as the window resizes. That is the model to copy
whether or not we keep the library.

**What is wrong today.** The HUD is placed with hand-tuned magic offsets —
`(40, window[1] - 76)`, `(window[0] - 263, window[1] - 162)`,
`(window[0] / 2 - 225, 0)` — numbers that only work because the HUD art happens
to be the size it is. The wave banner ignores the window entirely.

**Sequencing.** This should land *after* the splash and menu screens, not before.
Menus are the most layout-sensitive thing on the roadmap, and building anchoring
twice would be waste.

**Dependency note.** `pygame_gui` requires `pygame-ce>=2.5.3`; we pin 2.5.8, so
the AT2 fork decision already unblocks this.

---

## AT20 — Settings menu — SUPERSEDED by AT21–AT24

**Short description:** A mouse-driven settings screen for display and gameplay
options. Keyboard and controller navigation come later; the widget library
supports focus, so the structure should not need rewriting for it.

**Dependencies:** AT18 (shares `pygame_gui`)

**Goals**
- [ ] `SETTINGS` joins `PLAYING` / `PAUSED` as a named screen state
- [ ] Reachable from the pause screen; from the main menu once that exists
- [ ] Display options: vsync, frame cap, resolution
- [ ] Gameplay options: whatever we decide players should tune
- [ ] Settings persist between sessions
- [ ] Mouse only, but built so focus-based navigation can be added

**It fits the seam AT14 left.** Screen state is already a named pair rather than
a boolean precisely so this could be added by adding a name. Settings reached
*from pause* also sidesteps AT14's blocker: it overlays like the pause screen
does, so it does not need the ~30 locals lifted out of `game_loop` the way a
main menu that can *start* a game will.

**Widgets come from `pygame_gui`**, already adopted in AT18: `UIDropDownMenu`,
`UIHorizontalSlider`, `UIButton`, `UILabel`. Note there is **no checkbox
element** — an on/off like vsync is a two-item dropdown or a button that toggles
its own label. Focus management exists (`select()`, `unfocus()`, the manager's
focus system), which is the hook for controller support later.

### The part that needs designing: `config` is constants, settings are state

`shooter/config.py` is module-level constants read at import. A settings screen
needs mutable, persisted values, and the two do not compose. Demonstrated on the
current code:

**Most gameplay values are captured at construction.** Changing
`config.ZOMBIE_SPEED` from 360 to 999 mid-game left the existing zombie at 360
while newly spawned ones got 999. Seventeen call sites read config in
`__init__`, so a live change means "applies to new entities only" unless every
entity re-reads.

**Default arguments bind at import.** `dt=config.SIM_DT` was evaluated once when
the module loaded; setting `config.SIM_DT = 0.5` afterwards left the default at
0.0166. Any setting that feeds a default argument simply will not take effect.

So this ticket cannot just mutate `config`. Options to weigh:
- a `Settings` object passed to constructors, with `config` as its defaults
- keep `config` for constants, add a separate settings store for tunables
- accept "new entities only" and say so in the UI

That decision is the substance of the ticket; the widgets are the easy part.

### Which settings are actually safe

| setting | applying it |
|---|---|
| frame cap | live — it is only `clock.tick(n)` |
| vsync | needs `set_mode` again, which recreates the surface |
| resolution | same, and SCALED cannot go below 1080×720 (pygame #3709) |
| zombie speed / health | new spawns only, per the finding above |
| `SIM_HZ` | **do not expose** |

**`SIM_HZ` should not be a user setting.** AT16 made the simulation
deterministic at a fixed rate; letting players change it changes game feel and
throws away the property physics will depend on. If it is ever exposed it
belongs behind a debug flag, not in a settings menu.

**Persistence** should write to the platform's user-config directory, not into
the repo. A JSON file is sufficient; `.gitignore` should not need to know about
it.

**Open question for Aaron:** are the zombie options meant as a difficulty
feature for players, or a debug affordance for us? That changes where they live
and whether they need to be safe mid-game.

---

## AT21 — Screen stack, theme, and a navigable pause menu — DONE

**Short description:** The foundation the menus need: adopt `pygame_gui`, add a
base theme, turn the flat screen state into a stack, and give the pause overlay
real navigation to Settings and Dev.

**Dependencies:** AT17

**Goals**
- [x] Adopt `pygame_gui` and a `UIManager` owned by the screen layer
- [x] A base theme file, so everything after this inherits a look rather than inventing one
- [x] Screen **stack**, not a flat enum
- [x] Screens declare whether they overlay the game or replace it
- [x] Pause overlay gains buttons: Resume, Settings, Dev, Quit
- [x] Settings and Dev exist as stubs, reachable and dismissable

**Dev is gated on `config.DEV_TOOLS`.** The entry is built only when the flag is
on, so a release build drops the button without a second pause menu existing.

**Why a stack rather than more names.** AT14 introduced `PLAYING | PAUSED` as a
named state so more screens could be added by adding names. That holds for
siblings, but `pause → settings → back to pause` is nesting, not switching — a
flat enum has nowhere to record what "back" means. A stack of screens does, and
it is the difference between this working and being rewritten at the third
screen.

**Overlay versus full-screen is a property, not a special case.** Pause draws
the frozen frame behind a veil; the dev screen wants the whole display. If a
screen declares which it is, the loop stops special-casing pause the way it does
today.

**AT18 no longer owns adopting `pygame_gui`.** Both the HUD and the menus need
it, and two tickets adopting the same dependency is how themes end up
inconsistent. This ticket owns it; AT18 depends on it.

---

## AT22 — Layout grid, themed widgets, and a dev screen — DONE

**Short description:** A Bootstrap-style grid for arranging UI, thin themed
wrappers over the widgets `pygame_gui` already provides, and a full-screen dev
screen that exercises all of it.

**Dependencies:** AT21

**Goals**
- [x] `Grid` / `Row` laying out rectangles by span, like Bootstrap
- [x] Thin themed wrappers so call sites are ours, not the library's
- [x] Full-screen dev screen, reachable from pause
- [x] A gallery: every widget arranged by the grid, with light examples
- [x] Iterate on theming and UX here, not in the settings screen

**The grid is arithmetic, not a widget.** `pygame_gui` positions everything with
a `relative_rect`, so what we are missing is not a component — it is something
that *computes* those rects. `Grid` divides a rect into columns, `Row` splits
horizontally, a `Column` claims a span. It returns rectangles and nothing else.

That has a property worth having: no pygame, no display, no manager. It is pure
geometry, so it can be exhaustively unit-tested headlessly, which is exactly
where off-by-one layout bugs live.

**Deliberately dumb.** Fixed column count, explicit spans, explicit gutters. No
constraint solving, no auto-sizing, no reflow. A layout you can predict by
reading it is worth more here than a clever one, and the whole point is that
`pygame_gui` handles the widgets while we only decide where they sit.

**What it is for.** Arranging a setting as a row — a label claiming most of the
width and a `UICheckBox` claiming the rest — and having the next setting line up
underneath without anyone hand-tuning pixel offsets. That is the same problem
AT18 solves for the HUD, from the other direction.

**Only wrappers are needed for the rest.** Checked against the installed
`pygame_gui` 0.6.14: `UICheckBox`, `UISelectionList`, `UIDropDownMenu`,
`UIForm`, `UIPanel`, `UIWindow`, `UIScrollingContainer`, `UITextEntryLine` and
`UIConfirmationDialog` all exist. A thin `shooter/ui/widgets.py` keeps theme and
defaults in one place and gives the grid somewhere natural to live beside them.

**Naming carries the explanation.** No comments justifying layout maths — if a
`span`, a `gutter` or a `cell_rect` needs a paragraph to explain it, the name is
wrong. This is the house style and the grid is a good test of it.

**This is the iteration surface.** Theming and spacing get argued out on a
screen with no gameplay consequences, before the settings form depends on them.

**Answered.** The dev screen is gated on `config.DEV_TOOLS`, to be hidden and
built out when the game is productionised. The theme is the game's own military
palette rather than a plain dev look, so the gallery is a fair preview of what
the settings screen will look like.

**No `Column` class in the end.** A column is what a `Row` hands out, so it never
became a type of its own -- `row.cell(span)` returns a rectangle and that is the
whole idea. `Grid` and `Row` are the only two classes.

**Review fixes.** A checkbox built pre-checked used to post
`UI_CHECK_BOX_CHECKED` at construction, which the AT24 form would have read as
the player editing a field it was still drawing -- it now uses the library's
`initial_state`. `ScreenStack.push` builds the incoming screen before tearing
down the outgoing one, so a screen that cannot lay itself out is a no-op rather
than a destroyed menu. The dev gallery sizes its selector to the space it has
and now builds from 570px rather than 643px.

**Overflow is an exception, not a squeeze.** A row that does not fit or a cell
that overruns its columns raises `LayoutOverflowError` rather than silently
shrinking. It caught two real mistakes while the dev screen was being written.

---

## AT23 — Runtime settings store — DONE

**Short description:** The non-UI half of settings. Solve the problem AT20
uncovered: `config` is import-time constants and settings are mutable persisted
state.

**Dependencies:** none — pure logic, buildable in parallel with AT22

**Goals**
- [x] A settings object taking its defaults from `config`
- [x] Persist to the platform user-config directory, not the repo
- [x] Each setting declares when it applies: **live**, **new entities only**, or **boot only**
- [x] Load at start-up; unknown or invalid stored values fall back to defaults
- [x] Fully tested without any UI

**A third failure mode, found while classifying.** Beyond the two the ticket
already named, some modules copy a config value into a *new name* at import --
`projectiles.BULLET_DAMAGE`, `GunData.CLIP`, `game.INSTAKILL_SECONDS`. Changing
`config` afterwards does nothing at all, not even for new entities. Those names
cannot be settings until their readers are rewired, and an AST guard now fails
the build if one is ever added to the catalogue.

**The classification is checked, not asserted.** Every `live` and
`new entities` claim is verified against real game objects. That turned up two
things worth knowing: `PLAYER_HEALTH` is captured as a starting value but its
regeneration cap is read live, so raising it does reach an existing player; and
a stunned zombie re-reads `ZOMBIE_SPEED` when the stun expires, so
`new entities` is a promise that new ones always get the value, not that
existing ones never will.

**Invalid stored values fall back rather than clamp.** A value out of range is
treated as corrupt, not as a near-miss to be squeezed into range -- clamping
would silently run the game at a number the player never chose. `load()` returns
the names it rejected so AT24 can say so.

**Saves are atomic.** Written to a temporary file beside the target and moved
into place, so a crash mid-save leaves the previous settings rather than half a
file.

**Nothing is rewired.** Applying writes back onto the `config` module, so all
seventeen existing read sites keep working untouched. That is what makes this
ticket small enough to review.

**Why it is its own ticket.** It is the only genuinely hard part, it has no
visual component, and it is completely testable. Bundling it with a screen would
hide it behind UI review.

**The two failure modes it has to solve**, both verified on the current code:

Gameplay values are captured in `__init__`, so changing one mid-game leaves
existing entities stale — a zombie built before the change kept speed 360 while
new ones got 999. Seventeen call sites read `config` at construction.

Default arguments bind at import: `dt=config.SIM_DT` stayed 0.0166 after
`config.SIM_DT` was set to 0.5. Any setting feeding a default argument silently
does nothing.

**`SIM_HZ` stays out of settings.** AT16 bought determinism at a fixed rate;
exposing it discards the property physics will depend on.

**Loading a stored value must not look like an edit.** Audited every wrapper in
`shooter/ui/widgets.py` while reviewing AT22: construction is silent for all of
them, and a regression test now holds that. One setter is not --
`UICheckBox.set_state` posts `UI_CHECK_BOX_CHECKED`, which is right for a click
and wrong for populating a form from the store. Slider, dropdown and selector
all load silently, so this is one known method rather than a general hazard.
Whatever populates a form from this store either avoids `set_state` or ignores
events raised before the screen's first draw.

---

## AT24 — Settings screen — DONE

**Short description:** The form. Reads and writes the AT23 store, saves only on
an explicit Save, and warns before anything that needs a restart.

**Dependencies:** AT22, AT23

**Goals**
- [x] Form-based, laid out with the AT22 grid
- [x] Nothing persists until Save is clicked; leaving without saving discards
- [x] Boot-only settings show a `UIConfirmationDialog` before being accepted
- [x] Settings marked "new entities only" say so in the UI rather than appearing broken
- [x] Display section: vsync, frame cap, resolution
- [x] Gameplay section: none — the tunables are debug, see below

**Answered: the tunables are debug, not difficulty.** So the settings screen is
Display only and the tunables moved to the dev screen, under LIVE and NEW SPAWNS
headings that say when a change lands. A difficulty preset for players is a
later ticket if we want one.

**Controls are derived, not configured.** A setting already declares its type
and bounds, so the control follows: a switch is a checkbox, a fixed set of
options is a dropdown, a bounded number is a slider. Adding a setting to a
screen is adding its name to a tuple.

**Not `UIForm`.** The goal named it, but `UIForm` builds its own layout from a
dict of field types, which fights the AT22 grid and would have meant a second
way of positioning things. `Form` here is a list of `Field`s the grid places.

**`VSYNC` became a bool.** It was `1`, which rendered as a two-position slider.
`set_mode` takes a bool, so the setting is a switch and reads as one.

**`DEV_TOOLS` is on neither screen.** Turning it off from the dev screen would
remove the only way back to the dev screen.

**Controls are populated at construction, never through setters.** That is what
keeps the AT22 checkbox landmine defused, and a test asserts opening a form
raises no events.

**Save semantics matter more than they look.** Applying live while the user is
still dragging a slider means a half-configured game and no way to cancel. An
explicit Save also gives the confirmation dialog somewhere sensible to fire.

**Open question for Aaron:** are the zombie tunables a difficulty feature for
players, or a debug affordance for us? Difficulty belongs here; debug belongs on
the dev screen, where "new entities only" is acceptable rather than confusing.
