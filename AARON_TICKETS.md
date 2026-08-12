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

**Follow-up left open:** `requirements.txt` and `pyproject.toml` now both
declare the dependency, and `uv run` resolves from `pyproject.toml` rather than
the exact pin — so they can drift once a newer pygame-ce ships. Consolidating on
`uv.lock` as the single source of truth and dropping `requirements.txt` is the
clean end state, deliberately deferred to keep this change additive.

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

## AT5 — Fix gameplay bugs — TODO

**Short description:** Behaviour that is plainly wrong rather than merely stylistic.
Each one changes how the game plays, so they land together and get called out.

**Dependencies:** AT4

**Goals**
- [ ] Zombies never animate — `zombie.update_anim("MOVE")` is commented out in the main loop, so they slide toward the player in a fixed pose. Same for the `"ATTACK"` pose in `is_zombie_attacking`.
- [ ] `PowerUps.PowerUp_Selection` calls `random.randint(2, 2)` — hardcoded to Nuke, a debug leftover. Restore `1..4`; `InstaKill` and `MaxAmmo` have empty pickup handlers and need implementing.
- [ ] `Human.rot_center` rotates without recentering the rect, so the sprite drifts and grows as it turns. The correct version is sitting commented out directly beneath it.
- [ ] `Shot.changeX/changeY` compute Y velocity from `smallChangeX`. Currently inert — only the commented-out `update()` reads them — so delete the dead fields rather than fixing them.
- [ ] `pygame.sprite.collide_rect_ratio(.5)` in `is_zombie_attacking` builds a callable and discards it; the following line does a plain full-rect check. Decide which was intended.
- [ ] `Cash.cash_add_remove` rejects any purchase when the balance is exactly 0 or would land on 0, and never checks that the balance actually covers the cost.
- [ ] `Zombie.remove_health` guards the damage but not the payout, so a corpse pays $50 again on every further hit — reachable when two explosions overlap one zombie in a frame, since `game.py` keeps iterating explosions after `kill()`. Found in AT11 review; covered by a strict xfail.
- [ ] Fullscreen toggle reads `key.get_pressed()`, so holding `\` flips the mode every frame. Move to a `KEYDOWN` event.

---

## AT6 — Coordinate system and magic numbers — TODO

**Short description:** The window is 1080×720, but the code is littered with
constants from a 1920×1080 build that was never fully migrated.

**Dependencies:** AT5

**Goals**
- [ ] `Zombie.spawn_zombie` spawns against a 1920×1080 frame (`1081`, `1921`, `randint(1,192)*10`) — zombies appear at the wrong offsets
- [ ] `RadarScrn.draw` is called with `-cameraX+960, -cameraY+540` — hardcoded 1920/2, 1080/2
- [ ] `Data.width = 1920` / `height = 50` are module globals nothing reads
- [ ] World bounds `-5000+window[…]` are inlined in the camera clamp
- [ ] Centralize in `shooter/config.py`: window size, world size, speeds, damage, costs, wave scaling, colors
- [ ] Radar scale derives from world size instead of a hardcoded `/50`

---

## AT7 — Class attributes used as mutable instance state — TODO

**Short description:** Nearly every class declares its mutable state on the class
body (`health = 100.00`, `cash_amount = 0`, `zombie_speed = 6`). It works only
because `+=` on an int rebinds to the instance — a genuine landmine the moment
anyone introduces a list, dict, or a second instance that reads before writing.

**Dependencies:** AT6

**Goals**
- [ ] Move all mutable state into `__init__` across `Human`, `Zombie`, `gun_data`, `Cash`, `grenade_data`, `PowerUps`, `Wave_System`, `Shot`, `Grenade`, `stunGrenade`, and both detonate classes
- [ ] Drop `Human.player` / `Zombie.player`, computed at class-definition time from class attrs
- [ ] `Zombie.zombie_speed` reset in `zombie_speed_timer` re-reads a class constant — make it an instance default

---

## AT8 — Delete dead code — TODO

**Short description:** Eight years of commented-out experiments.

**Dependencies:** AT7

**Goals**
- [ ] `Shop_Gui` (never instantiated), commented-out `Zombies_Killed`, the `Clock` docstring stub
- [ ] `from CarePackage import PackageSystem` (module does not exist)
- [ ] Commented-out `Shot.update`, the `rot_center` alternate, assorted `#zombie.update_anim` lines
- [ ] `Data.width` / `Data.height` / `human_X` / `human_Y` globals
- [ ] `gun_data.reloading` renders to the screen from a data class — move the blit to the caller
- [ ] Unused `Assets/Sounds/gun audio.mp3` (superseded by `gunAudio.wav`), `Assets/blackBox.jpg`, `Assets/menu.png` — confirm before deleting

---

## AT9 — PEP 8 naming and import hygiene — TODO

**Short description:** Mechanical rename pass. Large diff, near-zero risk, so it
goes late — every earlier ticket would otherwise conflict with it.

**Dependencies:** AT8

**Goals**
- [ ] Classes to PascalCase: `gun_data` → `GunData`, `grenade_data` → `GrenadeData`, `Wave_System` → `WaveSystem`, `loadBackground` → `BackgroundSheet`, `grenadeDetonate` → `GrenadeDetonate`, `stunGrenade` → `StunGrenade`, `stunDetonate` → `StunDetonate`, `RadarScrn` → `RadarScreen`
- [ ] Methods/attrs to snake_case: `Move_With_Camera`, `PowerUp_Selection`, `Spawning_Location`, `Wave_Count`, `cameraX`, `changeX`, …
- [ ] Fix the `posistion` typo throughout (`get_posistion`, `move_posistion`, `reset_posistion`)
- [ ] Replace `from X import *` with explicit imports in `game.py`, `Zombie.py`, `waveSystem.py`
- [ ] Shadowed builtin: `type` as a class attribute on `Human` and `Zombie`

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

**Open consequence:** `requires-python = ">=3.10"` is once again an untested
claim, which is exactly what this ticket set out to fix. Either narrow it to
`>=3.14` to match what CI proves, or accept it as aspirational. Worth deciding
rather than leaving implicit.

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

## AT12 — Frame-rate independence — TODO

**Short description:** All movement, animation, timers, and cooldowns are counted
in frames and assume a locked 60 FPS. Anything that drops frames plays in slow
motion.

**Dependencies:** AT11

**Goals**
- [ ] Thread `dt` from `clock.tick(60)` through entity updates
- [ ] Convert speeds to px/second and timers to seconds (`stun_timer`, `reload_time`, `Wave_Timer`, `PowerUps.timer_count`, animation frame advance)
- [ ] Behaviour verified unchanged at 60 FPS, correct at 30 and 144
