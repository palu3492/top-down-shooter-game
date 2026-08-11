# Aaron Tickets

Modernization backlog for the Top-Down Shooter. One ticket ≈ one PR.
Work top to bottom — later tickets assume earlier ones have landed.

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

**Short description:** `PowerUps.Timer` loads `"Human.png"`, a file that has
never existed in this repo, so any power-up left on the field for ~400 frames
(~7s) takes the whole process down. Pulled out of AT4 and moved ahead of AT3
because it caps every QA session at seven seconds and blocks meaningful review
of the PRs that follow.

**Dependencies:** AT2

**Goals**
- [x] Remove the crash — the blink-before-expiry effect should not load a nonexistent file
- [x] Preserve the evident intent (flash the pickup as it nears expiry) rather than deleting the behaviour outright
- [x] Verify a power-up survives its full 1200-frame lifetime and expires cleanly
- [x] Verify picking one up still works

**Fix:** the blink swapped in a 10%-scaled `Human.png` — a file that has never
existed here, and a nonsensical thing to blink to even if it had. Replaced with
a transparent `Surface` of the same size, built once when the timer starts, so
the pickup visibly flashes out and back as intended. Net −3 lines.

**Non-goals:** everything else in AT4, the import-time asset loads in
`powerups.py`, and the `randint(2, 2)` power-up selection bug in AT5. This PR
fixes one crash and nothing else.

---

## AT3 — Asset path resolution + loader cache — TODO

**Short description:** Every asset path is a bare relative string like
`"Assets/cursor.png"`, so the game only runs with the repo root as cwd. Worse,
`Human.update_anim` and `Zombie.update_anim` hit the disk with
`pygame.image.load` **every frame, per sprite** — the single largest performance
problem in the codebase.

**Dependencies:** AT1

**Goals**
- [ ] `shooter/assets.py` resolving paths relative to the package, not cwd
- [ ] Memoized `load_image` / `load_sound` so each file is decoded once
- [ ] Preload animation frames into lists at construction time; per-frame code indexes a list
- [ ] All 20+ hardcoded `"Assets/..."` strings routed through the resolver
- [ ] Game launches correctly from an arbitrary working directory
- [ ] Measure FPS before/after and record the delta in the PR

---

## AT4 — Fix crashes and unsafe-shutdown paths — TODO

**Short description:** Live crash bugs and exit paths that only work by accident.

**Dependencies:** AT3

**Goals**
- [x] ~~`PowerUps.Timer` loads `"Human.png"`~~ — moved to AT2.2 and pulled ahead of AT3; it was capping QA sessions at 7 seconds
- [ ] `loadBackground.image_at`: `if colorkey is -1` should be `==`. Correction to an earlier draft of this ticket — verified on 3.14 that this form emits **no** SyntaxWarning (CPython only warns on bare literals, and `-1` parses as a unary op). It happens to work because -1 falls in CPython's small-int cache, so it is latent fragility rather than a live bug. Note the whole `colorkey` branch is currently unreachable: the only caller passes no colorkey.
- [ ] Replace `pygame.quit(); quit()` with `sys.exit()` — `quit()` is a `site` builtin and is absent under `python -S` or when frozen
- [ ] Move `pygame.mixer.init()` and the module-level `Sound(...)` loads out of `Projectiles.py` import time into explicit init
- [ ] Move `PowerUps.og_image = pygame.image.load(...)` off the class body (runs at import)

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

## AT10 — Lint, format, type-check, CI — TODO

**Short description:** Automate the standards the previous tickets establish so
they don't rot again.

**Dependencies:** AT9

**Goals**
- [ ] `ruff` config in `pyproject.toml`; repo passes `ruff check` and `ruff format --check`
- [ ] Type hints on public methods; `mypy` (or `ty`) clean at a chosen strictness
- [ ] `.github/workflows/ci.yml` running lint + tests on push and PR
- [ ] Pre-commit hooks

---

## AT11 — Tests for game logic — TODO

**Short description:** There are zero tests. The ammo/reload state machine, cash,
wave scaling, and damage math are pure logic and testable headlessly with
`SDL_VIDEODRIVER=dummy`.

**Dependencies:** AT10

**Goals**
- [ ] `pytest` + a conftest that forces the dummy SDL video/audio drivers
- [ ] Cover `gun_data` reload transitions (empty clip, partial clip, no reserve, manual reload)
- [ ] Cover `Cash` add/remove including the boundary cases AT5 fixes
- [ ] Cover `Wave_System` spawn counts and `5 + wave²` scaling
- [ ] Cover `Human` / `Zombie` damage, death, and regen
- [ ] A smoke test that constructs the game and steps N frames without raising

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
