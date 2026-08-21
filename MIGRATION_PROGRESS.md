# Migration Progress

## Purpose

This is the live execution tracker for the architecture migration defined in
`GAME_ARCHITECTURE_AND_MIGRATION_PLAN.md`.

The architecture plan owns direction, boundaries, phases, and exit criteria. This
file records current work, evidence, temporary compromises, and the next concrete
steps. Update it in the same change that completes or materially changes a work
package.

## Status Vocabulary

| Status | Meaning |
|---|---|
| Not started | No implementation work has begun |
| In progress | Work is actively underway |
| At risk | Work can continue, but a known issue threatens its exit criteria |
| Ready for integration | Focused work is complete but its checkpoint is not integrated |
| Complete | Exit criteria and required verification are satisfied |

## Current Position

| Field | Current value |
|---|---|
| Migration phase | Phase 1 — Characterize the current vertical slice |
| Phase status | In progress |
| Active work package | M1.6 — Define multi-map fixture contract and close Phase 1 |
| Application expected to run | Yes; no migration implementation has begun |
| Next integration checkpoint | End of Phase 4 — Shared damage pipeline |
| Last updated | 2026-08-21 |

## Confirmed Project Constraints

- Retain Python and pygame-ce.
- Prepare clean boundaries for eventual authoritative online multiplayer without
  implementing networking during the initial rewrite.
- Remove obsolete APIs, accidental behavior, and save compatibility when they
  obstruct the new architecture.
- Intermediate migration phases may leave the game temporarily unplayable.
- Restore an end-to-end working game at designated integration checkpoints.
- Use placeholder shapes for gameplay visuals and a text-only debug HUD.
- Keep Tiled/TMX map authoring while allowing its schema and runtime adapter to be
  redesigned.
- Support multiple reusable maps without hardcoded map assumptions.
- Allow mode and compatible-map selection between matches without restarting the
  application.

## Phase Overview

| Phase | Description | Status | Evidence / note |
|---:|---|---|---|
| 0 | Baseline and decision record | Complete | Baseline, smoke path, behavior classification, and test audit recorded |
| 1 | Characterize the current vertical slice | In progress | M1.1-M1.5 complete; M1.6 active |
| 2 | Neutral commands, events, and entity IDs | Not started | — |
| 3 | Authoritative actor state and world position | Not started | — |
| 4 | Unified health, damage, death, and attribution | Not started | Integration checkpoint 1 |
| 5 | Weapon operation and inventory integration | Not started | — |
| 6 | Reusable spawning | Not started | — |
| 7 | Neutral Match and game-mode boundary | Not started | Integration checkpoint 2 |
| 8 | Complete presentation separation | Not started | — |
| 9 | Prove reuse with a sandbox ruleset | Not started | Integration checkpoint 3 |
| 10 | Resume Zombie Survival feature development | Not started | Product development resumes |

## Active Work Package

### M1.6 — Define multi-map fixture contract and close Phase 1

**Status:** In progress

**Objective:** Define the smallest reusable Tiled/TMX vocabulary with two synthetic
maps, then review Phase 1 evidence before command/event/entity work begins.

**Scope:**

- Add two deliberately different synthetic TMX fixtures using one documented
  vocabulary for identity, bounds, supported modes, collision, and spawn metadata.
- Prove both fixtures normalize to the same test-side contract without branching on
  map identity.
- Record the contract as input to the later production map adapter.
- Review all Phase 1 gap dispositions and verification evidence.

**Non-goals:**

- Implementing the production map catalog or adapter before its migration phase.
- Migrating the current world map.
- Building map-selection UI.

**Acceptance criteria:**

- [ ] Two synthetic TMX fixtures use the same semantic vocabulary.
- [ ] Both normalize to the same neutral test contract without map-specific code.
- [ ] Map requirements and optional elements are explicit.
- [ ] Phase 1 evidence is reviewed and Phase 2 can begin.

**Verification evidence:**

Pending.

## Phase 0 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M0.1 | Establish automated baseline | Complete | — |
| M0.2 | Record current manual smoke path | Complete | M0.1 |
| M0.3 | Classify behavior: preserve, redesign, or delete | Complete | M0.1, M0.2 |
| M0.4 | Audit test intent and identify characterization gaps | Complete | M0.3 |
| M0.5 | Confirm Phase 0 exit evidence and open first ADRs only if needed | Complete | M0.4 |

## Phase 1 Work Packages

| ID | Work package | Status | Characterization gaps |
|---|---|---|---|
| M1.1 | Establish deterministic characterization harness | Complete | CHAR-005 foundation |
| M1.2 | Characterize fire, damage, death, removal, reward, and loot | Complete | CHAR-001, CHAR-002 |
| M1.3 | Characterize pause through authoritative state | Complete | CHAR-003 |
| M1.4 | Characterize Survival wave/preparation transition | Complete | CHAR-004 |
| M1.5 | Characterize command and match-lifecycle edge cases | Complete | CHAR-006 through CHAR-009 |
| M1.6 | Define multi-map fixture contract and close Phase 1 | In progress | CHAR-010 |

## Phase 0 Exit Review

- [x] Confirmed technology, compatibility, presentation, map, mode, and intermediate
  playability decisions are recorded in the architecture plan and this tracker.
- [x] Full pytest and Ruff baselines are recorded with reproducible commands.
- [x] Known failures are separated from future migration regressions.
- [x] The application launch and focused smoke paths are recorded.
- [x] Important legacy behavior is classified as preserve, redesign, delete, or
  unresolved product behavior.
- [x] Test intent and Phase 1 characterization gaps are audited.
- [x] Phase 1 work packages are defined.
- [x] No ADR is required before Phase 1. Current decisions are sufficiently captured
  by the approved architecture plan; the first ADR should be created only when an
  implementation choice among meaningful command/event/entity alternatives is
  selected.

## Verification Baseline

### Automated tests

| Date | Command | Result | Notes |
|---|---|---|---|
| 2026-08-21 | `uv run pytest` | 869 passed, 35 failed in 56.35s | 32 failures cascade from disabled zombie spawning; 3 independent failures recorded below |
| 2026-08-21 | `uv run pytest` after M1.1 | 875 passed, 35 failed in 64.07s | Six new harness tests pass; failure set matches recorded baseline |
| 2026-08-21 | `uv run pytest` after M1.3 | 881 passed, 34 failed in 35.10s | Nine combat/pause tests pass; obsolete BASE-004 test removed; remaining failures match recorded categories |
| 2026-08-21 | `uv run pytest` after M1.4 | 886 passed, 34 failed in 33.16s | Five Survival transition tests pass; failure categories remain unchanged |

### Static checks

| Date | Command | Result | Notes |
|---|---|---|---|
| 2026-08-21 | `uv run ruff check .` | 35 violations | 32 in untracked `tmp/tree-replacement/` scripts; 3 in tracked map tools |

### Manual smoke checks

| Date | Scenario | Result | Notes |
|---|---|---|---|
| 2026-08-21 | Launch with `uv run python main.py` | Launched | pygame initialized and the application remained running until intentionally interrupted after approximately six seconds |
| 2026-08-21 | Menu/gameplay smoke suite | 70 passed, 3 failed in 19.78s | `test_smoke`, startup/shutdown, display, scenes, menu, and shop; two failures require spawned zombies and one is BASE-004 |

### Reproducible pre-migration smoke path

At integration checkpoints, verify the applicable portions of this path:

1. Launch from the repository root.
2. Reach the main menu and start a match.
3. Move and aim through the normal input adapter.
4. Fire, reload, select equipment/weapons, and interact with a station.
5. Pause and resume without advancing authoritative match state while paused.
6. Resize or change display state without replacing match state.
7. Reach or trigger a match outcome when the active mode supports one.
8. Leave the match and return to application navigation.
9. Shut down without leaving pygame subsystems or match state alive.

Current limitations: zombie spawning is deliberately disabled, so enemy movement,
combat, loot, wave completion, and outcome paths cannot be exercised end to end in
the current default configuration. Switching among multiple modes/maps does not yet
exist and is a target behavior rather than a legacy smoke requirement.

## Behavior Classification

Behavior classification was completed in M0.3. Entries describe observable
behavior, not merely a legacy class or file.

### Preserve

- Fixed-timestep authoritative simulation with rendering allowed to interpolate
  independently.
- Clean application lifecycle: launch, navigate scenes, start a match, pause/resume,
  leave, and shut down without leaking match state.
- Pausing stops match simulation; non-pausing overlays do not implicitly stop it.
- Player-facing shooter controls as capabilities: move, aim, fire, reload, switch
  equipment, throw/use equipment, and interact. Exact key bindings remain settings
  or adapter policy rather than simulation behavior.
- Distinct weapon behavior through reusable definitions and per-instance runtime
  state: damage, cadence, ammunition, reload, spread, pellets, melee reach, and
  automatic/semi-automatic operation. Exact balance values are not preserved.
- A stable collision shape independent of a visual animation frame.
- World-coordinate collision and authored obstacle intent, though not the current
  collision implementation or exact current TMX object types.
- Tiled/TMX map authoring, with map collision and semantic metadata adapted into a
  neutral runtime model.
- Match-scoped state isolation: a new match does not inherit actors, health,
  inventory, cash, timers, projectiles, or outcomes from a prior match.
- Mode-owned outcomes and match summaries exposed to the application shell.
- Items, stacks, inventory capacity, weapon ownership, and ammunition as reusable
  mechanics, subject to redesign of their APIs and ownership.
- Interactions with physical world objects as a reusable capability.

### Intentionally redesign

- Replace the `Session` god object with neutral Match, World, systems, mode rules,
  commands, events, and presentation adapters.
- Replace camera-as-player-position with authoritative actor transforms and a
  presentation camera that follows a selected actor.
- Replace pygame events and direct key polling inside simulation/rules with explicit
  commands.
- Replace pygame sprite identity and sprite groups as authoritative entity state
  with stable entity IDs, world registration, and capability queries.
- Replace zombie-targeting projectiles and separate melee/explosion paths with one
  attributed damage/death pipeline governed by faction relationships.
- Replace enemy-owned cash rewards and removal detection with attributed domain
  events consumed by mode-specific reward and loot policy.
- Replace constructor-selected zombie positions with map-driven, constrained,
  seeded spawn selection controlled by mode policy.
- Replace `WaveSystem`/`LevelRules` pygame-group and window contracts with a neutral
  game-mode contract. Exact `5 + wave²` scaling is not preserved.
- Replace the current graphical HUD, radar, weapon art, and mode banners with
  read-only text/debug overlays during migration.
- Replace asset-bound player/zombie presentation with placeholder shapes and
  optional diagnostic labels while shared mechanics are built.
- Replace hardcoded `world_1.tmx`, coordinates, world size, shops, and spawn
  assumptions with a map catalog, validated shared TMX schema, and explicit match
  configuration.
- Replace the current one-route start flow with runtime mode and compatible-map
  selection between fresh matches.
- Move cash, grenade counts, health, ammunition, and other model state out of UI
  modules into authoritative shared or mode-specific state.
- Redesign shops as reusable interactions/economy mechanisms configured by Zombie
  Survival rather than owned by the shared session.
- Redesign resize/fullscreen behavior around presentation viewports without changing
  authoritative world state.

### Delete

- Legacy animation counters and animation `type` fields as requirements of the
  authoritative `Human` model.
- The current illustrated HUD and its asset/layout compatibility requirements.
- Import-path, constructor-signature, and class-shape compatibility for superseded
  legacy systems.
- Mid-migration save-file compatibility and serialization of exact legacy session
  state.
- Direct dependencies from shared simulation to `Zombie`, zombie sprite groups,
  Survival cash, waves, or a singleton human player.
- Direct simulation dependencies on pygame surfaces, fonts, sounds, animation
  frames, display size, and camera offsets.
- The temporary `ZOMBIE_SPAWNING_ENABLED` switch as a permanent game-mode control;
  spawn availability belongs to match/mode configuration.
- Tests whose sole purpose is to preserve deleted animation fields, obsolete APIs,
  exact legacy wave formulas, exact current map object composition, or graphical
  HUD layout.
- Temporary untracked art-generation scripts and artifacts as part of the supported
  product/lint surface, unless separately promoted into maintained tooling.

### Unresolved product behavior

These existing features are not architectural foundations and are not protected
until their product role is confirmed:

- harvesting world props and collecting crafting resources;
- random arcade power-ups such as nuke, max health, max ammo, and instakill;
- the current finite numbered-level/campaign progression alongside endless
  Survival.

They may later be implemented as reusable mechanisms or mode-specific policies, but
their current implementations and tests must not constrain the rewrite by default.

## Test Intent Audit

The suite currently collects 904 parametrized cases across 37 test modules. The
dispositions below apply to test intent, not necessarily to each current test body.
A durable behavior may receive a new test against a new boundary rather than keep
the legacy test unchanged.

| Test area | Disposition | Durable intent / migration note |
|---|---|---|
| Fixed step, determinism, frame-rate behavior | Preserve and adapt | Preserve tick-driven simulation, accumulator bounds, and rate-independent mechanics; replace animation/camera-specific assertions |
| Weapons and ammunition | Preserve and adapt | Strong coverage of cadence, reload, magazines, reserve, spread, pellets, melee geometry, and instance isolation; remove HUD rendering and zombie-specific target coupling |
| Items and inventory | Preserve and adapt | Preserve catalog lookup, stacking, capacity, add/remove, and ownership semantics behind the new inventory boundary |
| Health and actor lifecycle | Preserve and replace boundary | Preserve damage, nonnegative display values, death, and state isolation; replace concrete `Human`/`Zombie` and animation-state assertions |
| Session integration | Decompose | Retain command-to-outcome behaviors but replace direct assertions against the god object, camera movement, sprite groups, and concrete rules constructors |
| Collision and world bounds | Preserve and adapt | Preserve geometric correctness and authoritative world boundaries; do not preserve the current map's exact mix of ellipse/polygon objects |
| Spawning | Preserve policy intent, replace mechanism | Preserve valid/off-screen/reachable/deterministic placement concepts; replace constructor randomness, camera-origin assumptions, and concrete zombie creation |
| Waves and levels | Replace with mode tests | Preserve phase transitions, timers, composition, and outcomes only where Survival requires them; delete exact legacy formulas and current `LevelRules` API expectations |
| Cash, loot, shops, and power-ups | Move to mode/mechanism tests | Preserve generic wallet/transaction and interaction invariants where useful; test Survival rewards as event reactions, not enemy/UI side effects |
| Outcomes and scene lifecycle | Preserve and adapt | Preserve one reported outcome, stopped simulation after outcome, fresh retry state, and return to navigation; extend to selectable modes/maps |
| Settings | Preserve adapter behavior selectively | Preserve validated settings and isolation; remove zombie-specific debug settings and graphical form/layout expectations as their paths disappear |
| Map/background/world loading | Preserve adapter contract | Replace hardcoded `world_1` expectations with shared TMX schema, validation, catalog, and multi-map fixtures |
| Rendering interpolation | Preserve presentation principle | Retain interpolation without simulation mutation; rewrite around neutral snapshots and placeholder bindings |
| HUD, layout, anchors, title, sky, dev screen | Delete or replace | Current illustrated/layout-specific expectations do not constrain the debug overlay or future selection UI |
| Preload and asset binding | Delete or replace | Asset-specific preload requirements are not preserved during placeholder development |
| Progress/save files | Delete legacy compatibility | Exact save schema and numbered-level persistence do not constrain the rewrite; future progression receives a new external-to-match model |
| Instance implementation shape | Delete | Tests asserting fields in `vars()`, class structure, imports, or constructor shapes are not behavioral contracts |
| Startup, display, smoke, shutdown | Preserve and adapt | Retain application lifecycle and clean shutdown; extend smoke coverage to consecutive mode/map selections |
| Harvesting/crafting | Deferred | Do not characterize further until its future product role is confirmed |

### Obsolete test expectations already identified

- `Human` animation counters/type must exist on construction.
- The current map must contain at least one polygon and one ellipse obstacle.
- The first wave contains exactly five zombies and later waves follow `5 + wave²`.
- Player movement is represented by moving the camera while the player remains at
  screen center.
- HUD art, weapon images, anchor dimensions, sky visuals, and preload lists retain
  their current presentation.
- Current imports, constructors, pygame groups, and `Session` attributes remain
  stable.
- Exact current save/progress schema remains readable.

### Phase 1 characterization gaps

Priority describes what must be protected before the affected production path is
migrated, not final implementation order.

| ID | Priority | Missing or fragmented behavior contract |
|---|---:|---|
| CHAR-001 | P0 | One vertical test drives fire input through gameplay, consumes the equipped weapon's ammunition, produces an attack, applies nonlethal/lethal damage, removes the target once, and records one reward consequence |
| CHAR-002 | P0 | Damage distinguishes killed, despawned, expired, and otherwise removed actors so rewards and loot occur only for attributed kills |
| CHAR-003 | P0 | Pausing is verified by authoritative simulation ticks/state rather than animation-update counts or rendered frames |
| CHAR-004 | P0 | Clearing the last enemy causes exactly one Survival phase transition into preparation, then exactly one next-wave request after the timer/skip command |
| CHAR-005 | P0 | Random attack spread and spawn selection can be reproduced from an injected seed/source rather than module-level `random` |
| CHAR-006 | P1 | Dead/despawned behavior covered in M1.5; neutral/friendly targets are a new Phase 4 teams/damage-policy requirement because legacy code has no such concept |
| CHAR-007 | P1 | Reload, weapon swap, cooldown, and trigger-hold behavior survives command-driven control without depending on session internals |
| CHAR-008 | P1 | Two consecutive matches prove isolation of actors, commands, events, timers, inventory, currency, outcomes, and random sources |
| CHAR-009 | P1 | A match result is reported exactly once and application navigation can dispose it before constructing another configuration |
| CHAR-010 | P1 | Two synthetic TMX fixtures load into the same neutral schema and expose collision, bounds, spawn metadata, and mode requirements without map-specific branches |

Existing weapon, item, outcome, timing, collision, and lifecycle tests should be
reused as source material. New Phase 1 tests should assert observable contracts at
the narrowest useful boundary and avoid freezing the planned class/package tree.

## Temporary Adapters and Duplication

No migration adapters exist yet.

When one is introduced, record:

| Adapter | Why it exists | Introduced | Removal condition | Status |
|---|---|---|---|---|
| Legacy RNG injection defaults | `Zombie`, `Gun`, and `PowerUps` accept isolated RNGs while legacy callers still default to module randomness | M1.1 | Match owns and supplies its seeded random sources | Active |

## Known Failures and Risks

| ID | Type | Description | First observed | Blocks | Status |
|---|---|---|---|---|---|
| BASE-001 | Test configuration | 32 tests expect spawned zombies, but `config.ZOMBIE_SPAWNING_ENABLED` is intentionally `False`; wave, level, loot, movement, resolution, shop, scene, and session failures cascade from the empty groups | M0.1 | Clean test baseline | Recorded; do not fix in M0.1 |
| BASE-002 | Map/test drift | `test_world_obstacles_keep_their_tiled_geometry` expects a polygon obstacle, but the current `world_1.tmx` loader result contains none | M0.1 | Clean test baseline | Redesign: preserve authored collision semantics, not exact object-type composition |
| BASE-003 | Legacy test drift | Instance-state test expects `Human` animation counters/type that the current `Human` no longer initializes | M0.1 | Clean test baseline | Delete obsolete animation-field expectation |
| BASE-004 | Timing/test behavior | Pause-loop test records animation updates instead of authoritative state | M0.1 | Clean test baseline | Resolved in M1.3: obsolete test removed and replaced by three authoritative pause tests |
| BASE-005 | Ruff scope | 32 of 35 Ruff violations are in untracked temporary tree-replacement scripts under `tmp/` | M0.1 | Clean lint baseline | Recorded; decide exclusion/deletion separately |
| BASE-006 | Tracked lint | Three E501 violations exist in `tools/assemble_occlusion_cleanup.py` and `tools/feather_high_detail_map.py` | M0.1 | Clean lint baseline | Recorded; do not fix in M0.1 |

## Decisions and ADRs

No architecture decision records have been created. Create one only when a lasting
decision has meaningful alternatives and is expensive to reverse.

| ADR | Decision | Status | Related work package |
|---|---|---|---|
| — | — | — | — |

## Completed Work Log

| Date | Work | Evidence |
|---|---|---|
| 2026-08-21 | Created the live migration tracker and decomposed Phase 0 | This file |
| 2026-08-21 | Completed M0.1 automated baseline | `uv run pytest`: 869 passed/35 failed; `uv run ruff check .`: 35 violations |
| 2026-08-21 | Completed M0.2 launch and smoke baseline | Application launch succeeded; focused suite: 70 passed/3 baseline failures |
| 2026-08-21 | Completed M0.3 behavior classification | Preserve/redesign/delete inventory and unresolved product behavior recorded |
| 2026-08-21 | Completed M0.4 test-intent audit | Test-area dispositions and ten prioritized characterization gaps recorded |
| 2026-08-21 | Completed M0.5 Phase 0 exit review | Phase 0 exit checklist complete; no pre-Phase-1 ADR required |
| 2026-08-21 | Completed M1.1 deterministic characterization harness | Six harness tests pass; focused Ruff passes; full suite remains at 35 recorded failures |
| 2026-08-21 | Completed M1.2 combat consequence characterization | Three vertical combat tests plus six harness tests pass; focused Ruff passes |
| 2026-08-21 | Completed M1.3 authoritative pause characterization | Three pause tests pass; accumulator seam extracted; obsolete animation-count test removed |
| 2026-08-21 | Completed M1.4 Survival transition characterization | Five field-clear/timer/skip/next-wave tests pass; hidden pygame key polling removed |
| 2026-08-21 | Completed M1.5 command/lifecycle characterization | Four target, weapon-state, session-isolation, and outcome tests pass; focused Ruff passes |

## Next Action

Begin M1.6 by defining two synthetic TMX fixtures and one neutral test-side map
contract, then close Phase 1 if its evidence is complete.
