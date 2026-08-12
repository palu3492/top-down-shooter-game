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

## AT15 — Zombies spawn around the world origin, not the player — TODO

**Short description:** `spawn_zombie` places zombies on a ring anchored at world
`(0, 0)` and sized `1920×1080` — a resolution the game does not use. Found while
doing AT6; **not** fixed there because it changes spawn distances, which is a
balance change rather than a constant rename.

**Dependencies:** AT6

**Goals**
- [ ] Spawn just outside the current viewport rather than around the origin
- [ ] Retire `config.SPAWN_AREA` once the ring is camera-relative

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

## AT17 — Resizable window via SCALED — TODO

**Short description:** Let players size the window freely. Start with
`pygame.SCALED`, which is one flag rather than a rendering rewrite.

**Dependencies:** AT12

**Goals**
- [ ] `set_mode(WINDOW, pygame.SCALED | pygame.RESIZABLE)`
- [ ] Confirm mouse aiming still lands correctly — SCALED claims to scale mouse events for us
- [ ] Make the fullscreen toggle actually fill the display rather than re-opening at 1080×720
- [ ] Handle `WINDOWRESIZED`, not the legacy `VIDEORESIZE`
- [ ] Verify the documented limitation: a SCALED window may only be resized *larger* than its design size

**Why SCALED first.** The game keeps believing it renders 1080×720 while pygame
scales and letterboxes to preserve aspect ratio. Crucially the docs state
*"mouse events are scaled for you, so your game doesn't need to do it"* — which
matters here because aiming is raw mouse-position arithmetic.

**Two caveats, both real.** SCALED is still marked *"an experimental API and may
change in future releases"*, and pygame issue #3709 reports that a SCALED window
cannot be resized below its design resolution. Open and unresolved.

**The fallback if SCALED disappoints** is render-to-surface plus manual
letterboxing: draw to a fixed internal surface, scale it to the window
preserving aspect, blit centred with bars. More control, but mouse translation
becomes ours to write — the thing SCALED gives away free.

**Risk to check before committing.** If the 3D-ish direction leads to an OpenGL
context via ModernGL, scaling is handled by the GL viewport rather than by
SCALED. Worth confirming how the two interact before building anything on top of
SCALED.

---

## AT18 — Adaptive HUD via pygame_gui anchors — TODO

**Short description:** Scaling is not layout. Reposition HUD elements relative
to window edges instead of stretching a fixed-resolution image.

**Dependencies:** AT17

**Goals**
- [ ] Adopt `pygame_gui` and rebuild the HUD with anchors
- [ ] Replace the hand-tuned absolute offsets throughout `ui/hud.py`
- [ ] Fix the wave banner, currently fully absolute at `(300, 210, 500, 100)`
- [ ] Radar, ammo, health and cash all track their nearest corner

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
