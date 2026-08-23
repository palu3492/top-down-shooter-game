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
| Migration phase | Phase 10 — Resume Zombie Survival feature development |
| Phase status | In progress |
| Active work package | M10.6 — Add neutral enemy death cleanup |
| Application expected to run | Yes; production START GAME uses the shared Survival runtime |
| Next integration checkpoint | End of M10.6 — Bounded multi-wave entity lifecycle |
| Last updated | 2026-08-22 |

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
- Treat the current TMX map as incomplete; evolve a capability-based schema for
  boundaries, collision, destructibles, spawn data, gun-buy boxes, and other
  semantic objects as those mechanics are implemented.
- Allow mode and compatible-map selection between matches without restarting the
  application.

## Phase Overview

| Phase | Description | Status | Evidence / note |
|---:|---|---|---|
| 0 | Baseline and decision record | Complete | Baseline, smoke path, behavior classification, and test audit recorded |
| 1 | Characterize the current vertical slice | Complete | All ten characterization gaps dispositioned and verified |
| 2 | Neutral commands, events, and entity IDs | Complete | Boundary audit and exit criteria verified |
| 3 | Authoritative actor state and world position | Complete | Explicit map/spatial/camera/collision boundaries verified |
| 4 | Unified health, damage, death, and attribution | Complete | Shared attributed damage pipeline verified at integration checkpoint 1 |
| 5 | Weapon operation and inventory integration | Complete | Owner-independent weapon pipeline verified |
| 6 | Reusable spawning | Complete | Semantic, constrained, explicit-position spawning verified |
| 7 | Neutral Match and game-mode boundary | Complete | Match/mode boundary and integration checkpoint 2 verified |
| 8 | Complete presentation separation | Complete | Headless Match/snapshot and import boundaries verified |
| 9 | Prove reuse with a sandbox ruleset | Complete | Visible Sandbox and switching integration checkpoint verified |
| 10 | Resume Zombie Survival feature development | In progress | M10.6 active |

## Active Work Package

### M10.6 — Add neutral enemy death cleanup

**Status:** In progress

**Objective:** Remove defeated enemies from Match-owned stores through an
explicit neutral lifecycle so long Survival runs do not accumulate corpses and
stale entity state across waves.

**Planned scope:**

- Define reusable coordinated removal from registry and Match stores.
- Preserve first-lethal facts and rewards before cleanup.
- Keep death snapshot visibility deliberate rather than accidental.
- Verify multi-wave entity counts remain bounded and IDs are never reused.

## Most Recently Completed Work Package

### M10.5 — Enforce neutral map collision during movement

**Status:** Complete

**Objective:** Make shared actor movement respect authored TMX collision geometry
without moving collision decisions into pygame scenes or Survival-specific code.

**Planned scope:**

- Extend shared Match actor movement with neutral obstacle resolution.
- Preserve deterministic bounds and diagonal movement behavior.
- Apply the same movement seam to survivors, enemies, and future modes.
- Characterize incomplete/no-collision maps as valid open spaces.

**Acceptance criteria:**

- [x] Shared actor movement stops against authored neutral obstacles.
- [x] Diagonal movement slides along an unblocked axis.
- [x] Bounded substeps and refined contact prevent ordinary obstacle tunneling.
- [x] No-collision maps retain valid direct movement behavior.

**Verification evidence:**

M10.5 closes with 1103 passing tests and focused Ruff clean. Shared movement
uses authoritative Box/Circle bounds, TMX AABB/ellipse/polygon obstacles,
deterministic axis resolution, and world bounds without pygame or mode imports.
Both Sandbox and Survival already consume this seam; incomplete maps with no
collision use the existing direct movement path.

## Earlier Completed Work Package

### M10.4 — Integrate neutral kill rewards and economy

**Status:** Complete

**Objective:** Connect attributed neutral enemy deaths to Survival-owned cash
without putting reward policy into weapons, enemies, presentation, or shared
combat services.

**Planned scope:**

- Consume neutral kill facts exactly once under Survival rules.
- Award mode-owned cash only for eligible survivor kills.
- Expose the authoritative balance through existing immutable mode status.
- Preserve the seam needed for future reusable purchase interactions.

**Acceptance criteria:**

- [x] Eligible attributed survivor kills award mode-owned cash exactly once.
- [x] Non-lethal damage, misses, and repeated attacks on dead targets award nothing.
- [x] Cash persists across waves and is visible through immutable mode status.
- [x] A restarted Match begins with a new zero-balance wallet.

**Verification evidence:**

M10.4 closes with 1100 passing tests and focused Ruff clean. Reward eligibility
uses the shared damage result's first-lethal transition and stable attribution,
so it cannot double-award. The mode owns its reusable `SurvivalWallet`; queued
combat events remain untouched for other consumers, and the existing economy
service can consume the same wallet when authored purchase interactions arrive.

## Earlier Completed Work Package

### M10.3 — Integrate neutral weapons into visible Survival

**Status:** Complete

**Objective:** Replace the temporary direct-damage input with reusable,
owner-independent weapon operation and make its runtime state visible through
the debug snapshot path.

**Planned scope:**

- Attach a neutral starting loadout to the survivor.
- Route fire and reload through shared weapon operation values.
- Create attributed attacks from weapon output rather than UI-selected damage.
- Expose ammo, cooldown, and reload state in immutable snapshots/debug text.

**Acceptance criteria:**

- [x] The survivor owns a pygame-free neutral starting loadout.
- [x] Fire/reload use shared cooldown, ammo, reserve, and reload operations.
- [x] Weapon output drives attributed damage and immutable debug state.
- [x] Aim and target resolution replace the temporary first-living-enemy choice.

**Verification evidence:**

M10.3 closes with 1099 passing tests and focused Ruff clean. The direct
`DamageEnemy` command is gone; Survival fire consumes a neutral rifle's runtime
and produces attributed ballistic attack descriptions. Cursor input becomes
world-space aim at the pygame boundary, while shared neutral ray targeting
selects the nearest collision box deterministically within weapon range. Misses
still spend ammunition, and snapshots expose live weapon debug state.

## Earlier Completed Work Package

### M10.2 — Add neutral wave progression and contact combat

**Status:** Complete

**Objective:** Turn the first shared-runtime Survival slice into a repeatable
combat loop with escalating waves and an authoritative loss condition.

**Scope:**

- Transition cleared waves through a timed preparation phase.
- Spawn subsequent waves through the same deterministic neutral pipeline.
- Route overlapping enemy contact through attributed shared damage.
- End Survival when the neutral survivor's health is depleted.

**Acceptance criteria:**

- [x] Clearing a wave starts a visible, deterministic preparation countdown.
- [x] Countdown completion spawns a larger next wave with stable entity IDs.
- [x] Enemy overlap applies frame-rate-independent attributed contact damage.
- [x] Lethal contact damage produces a stable Survival loss result.
- [x] The visible application flow clearly handles loss and restart/exit.

**Verification evidence:**

M10.2 closes with 1097 passing tests and focused Ruff clean. Terminal Match
results are reported once to the application router, defeat opens the existing
text result overlay, and retry disposes the defeated Match before starting a
fresh neutral Survival Match at full health on wave one.

## Earlier Completed Work Package

### M10.1 — Establish the shared-runtime Survival vertical slice

**Status:** Complete

**Objective:** Rebuild the first playable Zombie Survival slice on the shared
Match runtime proven by Sandbox, beginning with neutral player/enemy spawning.

**Scope:**

- Construct Survival actors through neutral creation and spawn services.
- Advance their authoritative spatial/combat state through Match-owned systems.
- Present them through the shared snapshot placeholder path.

**Non-goals:**

- Restoring every legacy wave/shop/loot behavior in one package.
- Final graphics, animation, networking, or production HUD work.
- Production presentation styling.
- Production artwork, animation, or asset authoring.

**Acceptance criteria:**

- [x] Survival player and enemies are neutral Match entities, not sprite authority.
- [x] Initial spawning works through shared seeded placement.
- [x] Movement, health, damage, and death are visible through snapshots.
- [x] Obsolete spawning-disabled failures are retired or replaced by new intent tests.

**Verification evidence:**

M10.1 closes with 1093 passing tests and no failures. The MatchHost-backed
production START GAME route opens the neutral Survival scene on the retained TMX
map. WASD moves the survivor, the initial horde pursues, click attacks kill the
current living target, snapshots drive shapes/health/status, and pause/end-game
disposes the Match. Obsolete spawning-disabled and legacy sprite-authority tests
were removed or replaced with neutral runtime intent tests. The no-host direct
start remains only as an isolated compatibility harness, not the production route.

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
| M1.6 | Define multi-map fixture contract and close Phase 1 | Complete | CHAR-010 |

## Phase 2 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M2.1 | Define neutral command values and input adapter | Complete | Phase 1 |
| M2.2 | Introduce stable entity IDs and world registration seam | Complete | M2.1 |
| M2.3 | Define lifecycle/combat events and a small event queue | Complete | M2.2 |
| M2.4 | Route essential controls and mode requests through commands | Complete | M2.1, M2.3 |
| M2.5 | Verify Phase 2 boundaries and retire temporary polling paths | Complete | M2.4 |

## Phase 3 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M3.1 | Introduce neutral transforms and collision shapes | Complete | Phase 2 |
| M3.2 | Move the player through authoritative world position | Complete | M3.1 |
| M3.3 | Make the presentation camera follow the selected actor | Complete | M3.2 |
| M3.4 | Separate simulation collision from sprite rectangles | Complete | M3.2 |
| M3.5 | Parameterize world creation by neutral map data and close Phase 3 | Complete | M3.3, M3.4 |

## Phase 4 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M4.1 | Introduce neutral health and armor state | Complete | Phase 3 |
| M4.2 | Define damage requests/results and relationship policy | Complete | M4.1 |
| M4.3 | Route ranged, melee, explosion, contact, and power damage | Complete | M4.2 |
| M4.4 | Emit attributed death/removal facts and move rewards/loot | Complete | M4.3 |
| M4.5 | Verify shared damage pipeline and integration checkpoint 1 | Complete | M4.4 |

## Phase 5 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M5.1 | Separate weapon definitions from runtime state | Complete | Phase 4 |
| M5.2 | Route fire, reload, cooldown, and ammo through a neutral weapon service | Complete | M5.1 |
| M5.3 | Create attributed attacks through adapters and injected spread RNG | Complete | M5.2 |
| M5.4 | Reconcile carried equipment and backpack into an explicit loadout | Complete | M5.3 |
| M5.5 | Verify reusable weapon operation and close Phase 5 | Complete | M5.4 |

## Phase 6 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M6.1 | Define spawn data and TMX capability validation | Complete | Phase 5 |
| M6.2 | Add reusable spawn queries and placement constraints | Complete | M6.1 |
| M6.3 | Construct actors from explicit definitions and positions | Complete | M6.2 |
| M6.4 | Route Survival waves through the shared spawn service | Complete | M6.3 |
| M6.5 | Verify reusable spawning and close Phase 6 | Complete | M6.4 |

## Phase 7 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M7.1 | Define mode/map catalogs and Match configuration | Complete | Phase 6 |
| M7.2 | Introduce authoritative Match ownership | Complete | M7.1 |
| M7.3 | Establish narrow mode contract and package Zombie Survival | Complete | M7.2 |
| M7.4 | Expose mode status and remove rendering from rules | Complete | M7.3 |
| M7.5 | Add leave/select/start application flow | Complete | M7.4 |
| M7.6 | Verify disposal, consecutive matches, and integration checkpoint 2 | Complete | M7.5 |

## Phase 8 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M8.1 | Define read-only simulation snapshots | Complete | Phase 7 |
| M8.2 | Bind actors, attacks, and world objects to placeholder shapes | Complete | M8.1 |
| M8.3 | Replace the graphical HUD with a text debug overlay | Complete | M8.1 |
| M8.4 | Remove legacy sprite/UI authoritative-state bridges | Complete | M8.2, M8.3 |
| M8.5 | Verify headless Match advancement and close Phase 8 | Complete | M8.4 |

## Phase 9 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M9.1 | Define the sandbox mode contract and configuration | Complete | Phase 8 |
| M9.2 | Run reusable actors, movement, combat, and spawning under sandbox rules | Complete | M9.1 |
| M9.3 | Bind sandbox snapshots to the placeholder presentation | Complete | M9.2 |
| M9.4 | Verify mode/map switching and integration checkpoint 3 | Complete | M9.3 |

## Phase 10 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M10.1 | Establish the shared-runtime Survival vertical slice | Complete | Phase 9 |
| M10.2 | Add neutral wave progression and contact combat | Complete | M10.1 |
| M10.3 | Integrate neutral weapons into visible Survival | Complete | M10.2 |
| M10.4 | Integrate neutral kill rewards and economy | Complete | M10.3 |
| M10.5 | Enforce neutral map collision during movement | Complete | M10.4 |
| M10.6 | Add neutral enemy death cleanup | In progress | M10.5 |

## Phase 9 Exit Review

- [x] A non-Survival mode resolves through the shared catalog and Match lifecycle.
- [x] Sandbox reuses seeded spawning, stable IDs, spatial/combat/faction stores, damage, events, and snapshots.
- [x] Sandbox has no Zombie Survival or presentation dependency.
- [x] Shared placeholder presentation renders Sandbox without mutating simulation.
- [x] Sandbox is selectable and viewable from the main menu on the retained TMX map.
- [x] Pause/end-game and fresh Survival/Sandbox/map switching dispose state correctly.
- [x] Integration checkpoint 3 adds no failure category beyond the recorded baseline.

## Phase 8 Exit Review

- [x] Match snapshots are frozen, copied, and presentation-independent.
- [x] Placeholder actors, attacks, effects, pickups, and props render from snapshots.
- [x] Gameplay HUD and shop/context output use text-only immutable values.
- [x] Session does not construct retired HUD, radar, shop, or mode-banner objects.
- [x] Cash and equipment counters no longer originate in UI modules.
- [x] Match advances and snapshots in a fresh process that rejects pygame/UI imports.
- [x] Neutral TMX definitions do not import the pygame asset loader.
- [x] The full suite adds no failure category beyond the recorded baseline.

## Phase 7 Exit Review

- [x] Match owns configuration, lifecycle, tick, stores, events, damage, and RNG.
- [x] Modes use a narrow pygame-free lifecycle/status/result contract.
- [x] Zombie Survival policy is isolated under its mode package.
- [x] Mode/map compatibility is validated before Match construction.
- [x] The application can leave, select, and start again without process restart.
- [x] Pause covers gameplay without disposal; removal disposes exactly once.
- [x] Consecutive matches isolate actors, stores, cash, timers, RNG, and UI bindings.
- [x] Shared simulation and mode presentation boundary audits pass.
- [x] Integration checkpoint 2 launch smoke succeeds.
- [x] The full suite adds no failure category beyond the recorded baseline.

## Phase 6 Exit Review

- [x] TMX spawn points/regions normalize with semantic metadata.
- [x] Modes validate required map capabilities without map-identity branches.
- [x] Seeded spawn selection composes bounds, visibility, distance, occupancy, and collision.
- [x] Selection failures are explicit and do not construct actors.
- [x] Actor definitions/requests are neutral and creation receives explicit positions.
- [x] Production `Zombie` construction is isolated to one pygame adapter.
- [x] Survival owns wave timing/count only and uses shared spawning.
- [x] Authored sources and the named incomplete-map fallback are verified.
- [x] A non-Survival faction uses the same spawn pipeline and neutral world stores.
- [x] The full suite adds no failure category beyond the recorded baseline.

## Phase 5 Exit Review

- [x] Immutable weapon definitions are separate from per-instance runtime state.
- [x] Fire, reload, ammunition, cooldown, and refill use neutral operation results.
- [x] Controllers produce attributed attack descriptions before pygame adaptation.
- [x] Injected random sources make spread deterministic.
- [x] A non-player entity ID uses the same operation and attack contracts.
- [x] One production adapter owns current `Shot`/`Swing` construction.
- [x] Owner-independent loadouts preserve individual weapon runtime state.
- [x] Session and shop do not directly mutate weapon operation fields.
- [x] The full suite adds no failure category beyond the recorded baseline.

## Phase 4 Exit Review

- [x] Ranged, melee, explosive, and contact attacks route through shared damage policy.
- [x] Nuke behavior is explicitly a removal rather than attributed damage.
- [x] Applied damage and the first lethal transition emit exactly once with attribution.
- [x] Zombies neither receive nor mutate player cash.
- [x] Survival rewards and loot consume attributed kill facts.
- [x] Friendly-fire behavior is independently testable through relationship policy.
- [x] Integrated kill-to-removal/reward/loot behavior passes without spawning.
- [x] The full suite adds no failure category beyond the recorded baseline.

## Phase 3 Exit Review

- [x] Player and enemy actors have stable-ID-addressed world transforms.
- [x] Authoritative movement precedes presentation camera updates.
- [x] Camera and viewport changes cannot mutate world position.
- [x] Player collision uses neutral world-coordinate shapes.
- [x] World creation receives an explicit neutral map definition in production.
- [x] Incomplete TMX maps adapt with capability defaults rather than final-schema assumptions.
- [x] Two map definitions create worlds without identity-specific branches.

## Phase 2 Exit Review

- [x] Production gameplay input crosses one pygame-to-command adapter.
- [x] Essential actions are driven in tests without pygame events or key state.
- [x] Simulation and mode rules do not poll pygame input state.
- [x] Stable match-scoped entity IDs support explicit registration and removal.
- [x] Ordered lifecycle facts are observable without inspecting UI state.
- [x] Neutral command, event, and registry modules have no pygame dependency.
- [x] Legacy Session input wrappers are isolated and have a removal condition.

## Phase 1 Exit Review

- [x] Combat consequences and removal causes have behavioral coverage.
- [x] Pause and Survival transitions are driven through authoritative state.
- [x] Random-dependent mechanics expose reproducible injected sources.
- [x] Match lifecycle and weapon-operation boundaries have regression coverage.
- [x] Two different TMX fixtures normalize without map-identity branches.
- [x] The full suite adds no failures beyond the 34 recorded legacy failures.

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
| 2026-08-21 | `uv run pytest` after M1.6 | 894 passed, 34 failed in 39.45s | Four map-contract cases and M1.5 coverage pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M2.1 | 898 passed, 34 failed in 42.61s | Four command/input-adapter tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M2.2 | 902 passed, 34 failed in 29.60s | Four registry/legacy-bridge tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M2.3 | 906 passed, 34 failed in 30.37s | Four event-value/queue/bridge tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M2.4 | 908 passed, 34 failed in 30.93s | Essential actions execute from commands; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M2.5 | 911 passed, 34 failed in 30.04s | Three executable boundary-audit tests pass; Phase 2 exit criteria satisfied |
| 2026-08-21 | `uv run pytest` after M3.1 | 914 passed, 34 failed in 30.28s | Three neutral spatial-store/player-bridge tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M3.2 | 916 passed, 34 failed in 30.26s | World-transform movement/bounds tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M3.3 | 919 passed, 34 failed in 29.92s | Three camera-follow/presentation-isolation tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M3.4 | 923 passed, 34 failed in 30.59s | Four headless collision-shape tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M3.5 | 925 passed, 34 failed in 41.12s | Two production map-definition tests pass; Phase 3 exit criteria satisfied |
| 2026-08-21 | `uv run pytest` after M4.1 | 930 passed, 34 failed in 35.32s | Five neutral health/armor/store bridge tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M4.2 | 935 passed, 34 failed in 67.94s | Five attributed damage/relationship-policy tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M4.3 | 940 passed, 34 failed in 83.63s | Five routed attack/faction tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M4.4 | 944 passed, 33 failed in 53.65s | Attributed damage/death and event-driven Survival consequences pass; one obsolete snapshot-loot test removed; remaining failures match recorded categories |
| 2026-08-21 | `uv run pytest` after M4.5 | 945 passed, 33 failed in 61.82s | Integrated kill-to-removal/reward/loot proof passes; Phase 4 closes with only recorded failure categories |
| 2026-08-21 | `uv run pytest` after M5.1 | 950 passed, 33 failed in 44.56s | Five definition/runtime and adapter tests pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M5.2 | 955 passed, 33 failed in 32.28s | Neutral operation requests/results preserve ammo, reload, cooldown, and timing behavior; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M5.3 | 959 passed, 33 failed in 29.96s | Attributed neutral attack descriptions and the sole sprite adapter pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M5.4 | 965 passed, 33 failed in 29.71s | Explicit loadout/inventory, shop integration, selection, and runtime preservation pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M5.5 | 969 passed, 33 failed in 30.82s | Non-player operation, refill routing, construction-site audit, and mutation-boundary audit pass; Phase 5 closes |
| 2026-08-21 | `uv run pytest` after M6.1 | 973 passed, 33 failed in 32.16s | Neutral point/region parsing, metadata, offsets, supported modes, and capability reports pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M6.2 | 978 passed, 33 failed in 33.32s | Deterministic semantic queries and composable placement constraints pass; explicit failure replaces origin fallback |
| 2026-08-21 | `uv run pytest` after M6.3 | 985 passed, 33 failed in 37.65s | Neutral actor creation, explicit-position adapter, production construction audit, and wave wiring pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M6.4 | 989 passed, 33 failed in 31.95s | Shared batch spawning, authored enemy regions, explicit failures, and named legacy fallback pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M6.5 | 992 passed, 33 failed in 34.15s | Non-Survival spawn/registry proof and pygame/rules boundary audits pass; Phase 6 closes |
| 2026-08-21 | `uv run pytest` after M7.1 | 999 passed, 33 failed in 33.42s | Stable catalogs, immutable configuration, lightweight metadata, and structured compatibility resolution pass |
| 2026-08-21 | `uv run pytest` after M7.2 | 1005 passed, 33 failed in 45.08s | Match lifecycle, owned stores, named deterministic RNG, disposal, compatibility rejection, and Session bridge pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M7.3 | 1009 passed, 33 failed in 53.40s | Narrow mode lifecycle, Survival package ownership, reusable economy, mode cash/outcome state, and compatibility imports pass; failure categories remain unchanged |
| 2026-08-21 | `uv run pytest` after M7.4 | 1010 passed, 33 failed in 45.24s | Immutable mode status and Match status/result access pass; countdown presentation consumes snapshots; wave/level rules have no pygame or UI imports |
| 2026-08-21 | `uv run pytest` after M7.5 | 1015 passed, 33 failed in 45.00s | Application-owned selection, pre-allocation compatibility checks, cover-vs-remove lifecycle, explicit leave, and fresh restart pass |
| 2026-08-21 | `uv run pytest` after M7.6 | 1020 passed, 33 failed in 28.60s | Consecutive-match isolation, exact-once disposal, shared/mode boundary audits, and integration checkpoint 2 pass; Phase 7 closes |
| 2026-08-22 | `uv run pytest` after M8.1 | 1025 passed, 33 failed in 32.18s | Frozen match/entity/combat/weapon snapshots, copied runtime values, immutable mode payload validation, and first presentation consumer pass |
| 2026-08-22 | `uv run pytest` after M8.2 | 1029 passed, 33 failed in 44.19s | Tag-driven placeholder actors, attacks, effects, pickups, and interactables render from snapshots over the retained TMX map |
| 2026-08-22 | `uv run pytest` after M8.3 | 1034 passed, 33 failed in 34.86s | Text-only debug overlay reports Match, mode, player, vitality, weapon, equipment, cargo, and context from immutable values; legacy graphical HUD is not drawn |
| 2026-08-22 | `uv run pytest` after M8.4 | 1037 passed, 33 failed in 25.77s | Legacy graphical components are not constructed; neutral cash/equipment state and frozen shop/context values feed the text overlay |
| 2026-08-22 | `uv run pytest` after M8.5 | 1040 passed, 33 failed in 26.38s | Fresh-process headless Match advancement/snapshot, static presentation audit, and pygame-free map path resolution close Phase 8 |
| 2026-08-22 | `uv run pytest` after M9.1 | 1045 passed, 33 failed in 28.20s | Cataloged non-Survival Sandbox lifecycle, finite/open-ended result policy, immutable status snapshots, disposal, and dependency audit |
| 2026-08-22 | `uv run pytest` after M9.2 | 1048 passed, 33 failed in 28.37s | Two neutral factions reuse seeded spawning, stable IDs, spatial/combat stores, movement, relationship-aware attributed damage, events, and snapshots |
| 2026-08-22 | `uv run pytest` after M9.3 | 1051 passed, 33 failed in 27.70s | Shared snapshot presenter draws Sandbox actors and generic text status without mutating Match tick, position, or health |
| 2026-08-22 | `uv run pytest` after M9.4 | 1054 passed, 33 failed in 49.80s | Main-menu Sandbox route, TMX-backed scene, controls, combat, pause/end flow, and fresh Survival/Sandbox/map switching close Phase 9 |
| 2026-08-22 | `uv run pytest` during M10.1 shared actor extraction | 1056 passed, 33 failed in 35.00s | Mode-independent Match actor spawn/registration/movement utility replaces Sandbox-owned orchestration before Survival adoption |
| 2026-08-22 | `uv run pytest` during M10.1 neutral Survival rules | 1060 passed, 33 failed in 29.14s | Neutral survivor/initial-horde spawning, pursuit/movement, attributed enemy death, events, mode status, and immutable snapshots |
| 2026-08-22 | `uv run pytest` during M10.1 visible Survival integration | 1063 passed, 33 failed in 34.35s | Production START GAME now uses TMX-backed neutral Survival snapshots, movement, pursuit, click damage, pause, and clean disposal |
| 2026-08-22 | `uv run pytest` after M10.1 | 1093 passed in 50.76s | Removed the spawning-disable switch and obsolete sprite-era expectations; current and legacy TMX collision layer names remain supported; failure ledger is clean |
| 2026-08-22 | `uv run pytest` during M10.2 neutral loop | 1096 passed in 28.47s | Timed preparation, escalating deterministic respawn, attributed contact damage, and survivor loss run through Match-owned state |
| 2026-08-22 | `uv run pytest` after M10.2 | 1097 passed in 28.46s | Neutral terminal results open defeat UI once; retry disposes the old Match and creates an isolated full-health wave-one Survival Match |
| 2026-08-22 | `uv run pytest` during M10.3 neutral weapon integration | 1098 passed in 24.58s | Neutral equipped rifle/loadout, cooldown, ammunition, reload, attributed ballistic attacks, and snapshot debug state replace direct-damage input |
| 2026-08-22 | `uv run pytest` after M10.3 | 1099 passed in 24.20s | Cursor-to-world aim, deterministic nearest-box ray targeting, range limits, and ammunition-consuming misses close reusable weapon-driven Survival combat |
| 2026-08-22 | `uv run pytest` after M10.4 | 1100 passed in 24.58s | First-lethal attributed enemy kills award the mode-owned wallet once; balance snapshots, wave persistence, event availability, and restart isolation pass |
| 2026-08-22 | `uv run pytest` after M10.5 | 1103 passed in 24.46s | Shared collision-aware movement stops flush, slides by axis, supports Box/Circle actor bounds and TMX obstacle shapes, and preserves open-map movement |

### Static checks

| Date | Command | Result | Notes |
|---|---|---|---|
| 2026-08-21 | `uv run ruff check .` | 35 violations | 32 in untracked `tmp/tree-replacement/` scripts; 3 in tracked map tools |

### Manual smoke checks

| Date | Scenario | Result | Notes |
|---|---|---|---|
| 2026-08-21 | Launch with `uv run python main.py` | Launched | pygame initialized and the application remained running until intentionally interrupted after approximately six seconds |
| 2026-08-21 | Menu/gameplay smoke suite | 70 passed, 3 failed in 19.78s | `test_smoke`, startup/shutdown, display, scenes, menu, and shop; two failures require spawned zombies and one is BASE-004 |
| 2026-08-21 | Integration checkpoint 2 launch with `uv run python main.py` | Launched | pygame initialized and the application remained running until intentionally interrupted after approximately nine seconds |

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
- Progressive map authoring: incomplete maps remain loadable, while each mode
  validates only the capabilities it requires before match creation.
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
- Extend TMX semantics through neutral definitions for boundaries, collision,
  destructibles, spawn points/regions, gun-buy boxes, and later authored objects;
  never infer the final schema from today's incomplete map.
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
| Legacy Session input wrappers | `Session.handle` and `Session.step` adapt pygame events/key state for existing callers while production gameplay supplies neutral commands | M2.1 | Legacy tests/callers use `ActionCommand` and `ControlFrame`; remove during Session decomposition | Active |
| Player spatial snapshot bridge | `Session` records a neutral player transform while legacy camera offsets still drive movement | M3.1 | M3.2 makes the transform authoritative and derives the legacy camera from it | Removed in M3.2 |
| Legacy camera compatibility setters | Old callers can assign `camera_x`/`camera_y`, which repositions the authoritative player and resynchronizes the follow camera | M3.2 | Legacy tests stop positioning the player through camera offsets | Active |
| Legacy obstacle normalization | Session converts current pygame/TMX obstacle and prop rectangles into neutral collision values at query time | M3.4 | Production map adapter and world object lifecycle supply/update neutral collision directly | Active |
| Default Session map | Direct legacy `Session(...)` calls adapt the current TMX when no map definition is supplied; production `GameplayScene` passes one explicitly | M3.5 | Legacy callers pass match configuration/map definition | Active |
| Legacy combat-state mirror | Player/enemy actor-owned health is mirrored into the stable-ID combat store while old attacks still mutate actors directly | M4.1 | M4.3 routes attacks through the damage service and makes combat state authoritative | Removed from attack paths in M4.3 |
| Legacy actor health reflection | Authoritative damage results are copied to `Human.health`/`Zombie.zombie_health` for current rendering, outcomes, and regeneration | M4.3 | Presentation reads combat state and vitality effects route through shared services | Active |
| Legacy held-weapon properties | `Gun`/`Blade` expose `loaded`, `reserve`, cooldown, reload, and method results while neutral runtime/service own weapon operation | M5.1 | Callers consume explicit weapon-operation state/results | Active |
| Legacy projectile adapter | Neutral attributed attack descriptions become current `Shot`/`Swing` sprites and gunshot audio in one pygame-facing adapter | M5.3 | Projectile simulation and presentation consume neutral attacks directly | Active |
| Legacy carried/equipped view | `Session.carried` and `Session.equipped` adapt old list assignment/slicing onto the authoritative loadout | M5.4 | Legacy tests and UI consume `ActorInventory`/`Loadout` directly | Active |
| Legacy direct Zombie placement | Direct `Zombie(...)` callers still choose a legacy ring position when no explicit position is supplied; production waves use the actor factory | M6.3 | Tests/callers construct through actor creation requests and shared spawning | Active |
| Legacy Session/Match bridge | `Session` aliases Match-owned stores while it still owns pygame groups and presentation orchestration | M7.2 | Gameplay/presentation consumes Match directly and Session is decomposed | Active |
| Legacy Survival module imports | Former `systems.waves`, `systems.shop`, and `systems.survival_consequences` paths re-export mode-owned policy for existing callers/tests | M7.3 | Callers use the mode package and obsolete module paths are deleted | Active |
| Legacy Session mode-status bridge | Session builds immutable status from legacy rule state for Match snapshots and the text overlay | M7.4 | Match hosts the concrete mode instance and exposes its status directly | Active |
| Legacy Session snapshot inputs | Session supplies its player loadout and legacy-hosted mode status while Match state migrates into the snapshot builder | M8.1 | Match owns inventories and its concrete mode, requiring no Session-provided snapshot inputs | Active |
| Legacy visual-source registry | Session assigns stable IDs and spatial state to legacy projectile/pickup/prop objects without emitting gameplay lifecycle facts | M8.2 | These objects are created directly as neutral Match entities | Active |
| Legacy presentation status | Session copies grenades, transient effects, cargo, notices, and interaction context into a frozen value for the debug overlay | M8.3 | These values are included in Match-owned snapshots/read models | Active |

## Known Failures and Risks

| ID | Type | Description | First observed | Blocks | Status |
|---|---|---|---|---|---|
| BASE-001 | Test configuration | Legacy tests depended on a global switch that disabled zombie spawning and caused cascading empty-group failures | M0.1 | Clean test baseline | Resolved in M10.1: switch removed; relevant spawn behavior is covered through neutral runtime tests; obsolete legacy expectations deleted |
| BASE-002 | Map/test drift | A test coupled collision coverage to the unfinished production TMX object's exact geometry mix | M0.1 | Clean test baseline | Resolved in M10.1: stable semantic TMX fixtures cover ellipse/polygon preservation; loader accepts current `Collision` and transitional `Obstacles` names |
| BASE-003 | Legacy test drift | Instance-state test expected obsolete `Human` animation counters/type | M0.1 | Clean test baseline | Resolved in M10.1: obsolete sprite-animation field expectation removed |
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
| 2026-08-21 | Completed M1.6 and Phase 1 | Two synthetic TMX maps pass four neutral contract cases; full suite has only 34 recorded legacy failures |
| 2026-08-21 | Completed M2.1 neutral command boundary | Immutable primitive-only controls/actions, pygame adapter, gameplay movement, and reload path verified |
| 2026-08-21 | Completed M2.2 stable entity identity | Match-scoped monotonic IDs, neutral lookup/query/removal, and player/enemy legacy bridge verified |
| 2026-08-21 | Completed M2.3 domain-event seam | Immutable lifecycle/combat facts, ordered match queue, isolation, and registry lifecycle emission verified |
| 2026-08-21 | Completed M2.4 essential command routing | Fire, reload, selection, equipment, interaction, shop semantics, and phase skip route through neutral values |
| 2026-08-21 | Completed M2.5 and Phase 2 | Executable audit confirms one production input adapter, pygame-free neutral values, stable IDs, and ordered lifecycle facts |
| 2026-08-21 | Completed M3.1 neutral spatial state | Immutable transforms and box/circle shapes, ID-addressed store operations, and viewport-independent player snapshot verified |
| 2026-08-21 | Completed M3.2 authoritative player movement | Commands update bounded world transforms first; legacy camera offsets are derived and compatibility writes cannot silently diverge |
| 2026-08-21 | Completed M3.3 presentation camera extraction | Stable-ID follow camera clamps offsets, viewport resize is presentation-only, and world interactions use authoritative position |
| 2026-08-21 | Completed M3.4 neutral player collision | Headless AABB/ellipse/polygon overlap and world-coordinate obstruction replace camera/sprite-dependent player checks |
| 2026-08-21 | Completed M3.5 and Phase 3 | Neutral TMX adapter, explicit production map selection, two-map world creation, and enemy spatial synchronization verified |
| 2026-08-21 | Completed M4.1 neutral combat state | Stable-ID health, bounded depletion/restoration, optional armor, actor isolation, and legacy health mirroring verified |
| 2026-08-21 | Completed M4.2 damage policy | Primitive attribution, deterministic results, armor accounting, first-lethal transition, and configurable relationships verified |
| 2026-08-21 | Completed M4.3 shared attack routing | Ballistic, melee, explosive, and contact attacks use stable-ID damage service; policy precedes mutation; nuke stays a removal |
| 2026-08-21 | Completed M4.4 attributed consequences | Damage and first-lethal facts carry attribution; Survival owns cash/loot policy; enemies no longer hold cash; despawns and nukes award nothing |
| 2026-08-21 | Completed M4.5 and Phase 4 | Production attack audit and integrated consequence proof pass; full suite is 945 passed/33 recorded failures |
| 2026-08-21 | Completed M5.1 weapon state separation | Immutable pygame-free definitions and isolated runtime ammo/timers now back legacy equipment through compatibility properties |
| 2026-08-21 | Completed M5.2 neutral weapon operation | Explicit requests/results now govern readiness, fire, ammo, reload, cooldown, and timer advancement without actors or pygame |
| 2026-08-21 | Completed M5.3 neutral attack creation | Controllers can produce immutable attributed ballistic/melee descriptions; injected spread precedes the sole pygame projectile adapter |
| 2026-08-21 | Completed M5.4 explicit loadout | Owner-independent slots preserve weapon runtimes; Session/shop use loadout operations; stackable cargo remains an explicit backpack boundary |
| 2026-08-21 | Completed M5.5 and Phase 5 | Non-player weapon use and executable bypass audits pass; full suite is 969 passed/33 recorded failures |
| 2026-08-21 | Completed M6.1 spawn map contract | TMX points/regions and semantic metadata normalize neutrally; modes can validate required capabilities while incomplete maps remain loadable |
| 2026-08-21 | Completed M6.2 spawn selection | Role/tag/faction/kind queries and seeded box/ellipse/polygon sampling compose bounds, visibility, distance, occupancy, and collision constraints |
| 2026-08-21 | Completed M6.3 explicit actor creation | Neutral definitions/requests create the same actor at explicit positions; production `Zombie` construction is isolated to one pygame adapter |
| 2026-08-21 | Completed M6.4 Survival spawn routing | Survival owns counts/timing only; shared service selects and constructs batches from authored sources or the explicit legacy-ring fallback |
| 2026-08-21 | Completed M6.5 and Phase 6 | Neutral spawn pipeline and non-Survival world-store integration pass; full suite is 992 passed/33 recorded failures |
| 2026-08-21 | Completed M7.1 pre-match selection data | Stable mode/map catalogs resolve immutable seeded configurations or structured missing-capability reports before state construction |
| 2026-08-21 | Completed M7.2 authoritative Match ownership | Match now owns lifecycle, tick, events, registries, simulation stores, damage policy, and deterministic named RNG; Session temporarily consumes that owner; full suite is 1005 passed/33 recorded failures |
| 2026-08-21 | Completed M7.3 mode packaging | Match uses a narrow explicit lifecycle; Survival owns waves, rewards, shop stock/prices, cash, and outcome policy while reusable purchasing remains shared; full suite is 1009 passed/33 recorded failures |
| 2026-08-21 | Completed M7.4 read-only mode status | Frozen Survival snapshots now carry phase/wave/timing/cash/enemy/outcome data; Match exposes status/result and pygame countdown drawing lives only in presentation; full suite is 1010 passed/33 recorded failures |
| 2026-08-21 | Completed M7.5 application selection flow | MatchHost owns catalogs/configuration and one active Match; incompatible choices allocate nothing; pause preserves gameplay while removal disposes it; leave/select/start works without process restart; full suite is 1015 passed/33 recorded failures |
| 2026-08-21 | Completed M7.6 and Phase 7 | Consecutive matches isolate simulation/mode/presentation state; disposal is idempotent; executable boundary audits and launch smoke pass; full suite is 1020 passed/33 recorded failures |
| 2026-08-22 | Completed M8.1 immutable snapshots | Match snapshots copy stable-ID entity, spatial, collision, vitality, faction, weapon runtime, mode status, and result values; mutable nested mode payloads are rejected; full suite is 1025 passed/33 recorded failures |
| 2026-08-22 | Completed M8.2 placeholder world bindings | Stable tags select debug shapes for actors, melee/ballistic attacks, grenades, effects, pickups, and interactables; renderer reads snapshots only and TMX remains beneath it; full suite is 1029 passed/33 recorded failures |
| 2026-08-22 | Completed M8.3 text debug HUD | Gameplay no longer draws radar or image-backed health/cash/weapon/grenade/wave panels; one text overlay consumes immutable Match and presentation values; full suite is 1034 passed/33 recorded failures |
| 2026-08-22 | Completed M8.4 presentation cleanup | Session no longer constructs legacy HUD/radar/shop/mode panels; cash and equipment state are presentation-independent; frozen shop offers replace the graphical shop overlay; full suite is 1037 passed/33 recorded failures |
| 2026-08-22 | Completed M8.5 and Phase 8 | Match lifecycle and snapshots run while pygame/UI imports are rejected; neutral map path resolution removes the discovered transitive pygame dependency; full suite is 1040 passed/33 recorded failures |
| 2026-08-22 | Completed M9.1 sandbox mode boundary | A cataloged bounds-only Sandbox mode advances and snapshots through Match with its own immutable status/result and no Survival or presentation dependency; full suite is 1045 passed/33 recorded failures |
| 2026-08-22 | Completed M9.2 shared mechanics reuse | Red/blue generic actors deterministically spawn, move, take attributed hostile damage, and snapshot through shared Match stores without Session or sprites; full suite is 1048 passed/33 recorded failures |
| 2026-08-22 | Completed M9.3 sandbox snapshot presentation | Mode-neutral presenter and debug overlay draw Sandbox actors/status from immutable snapshots and cannot advance authoritative state; full suite is 1051 passed/33 recorded failures |
| 2026-08-22 | Completed M9.4 and Phase 9 | Sandbox is visible from the main menu with TMX, controls, combat, pause/exit, and isolated cross-mode/map restart; integration checkpoint 3 passes with 1054 passed/33 recorded failures |
| 2026-08-22 | Began M10.1 shared Survival vertical slice | Extracted neutral Match actor registration and movement from Sandbox; both modes can now reuse one pygame-free entity/spatial/combat/faction seam; full suite is 1056 passed/33 recorded failures |
| 2026-08-22 | Added M10.1 neutral Survival rules | Survivor and initial horde now run through shared Match spawning, movement, combat, events, and snapshots without sprites or legacy Session; full suite is 1060 passed/33 recorded failures |
| 2026-08-22 | Added M10.1 visible neutral Survival route | MatchHost-backed START GAME now presents the shared-runtime survivor/horde slice over TMX with controls, combat, status, pause, and exit; full suite is 1063 passed/33 recorded failures |
| 2026-08-22 | Completed M10.1 shared-runtime Survival vertical slice | Neutral actors, seeded spawning, pursuit/movement, attributed damage/death, snapshot presentation, and production routing pass; obsolete spawning-disabled and sprite-era expectations retired; full suite is 1093 passed with no failures |
| 2026-08-22 | Added M10.2 neutral wave and loss rules | Cleared waves enter preparation and spawn a larger deterministic wave; overlapping enemies deal attributed time-scaled damage; lethal contact produces `LOST`; full suite is 1096 passed |
| 2026-08-22 | Completed M10.2 repeatable Survival loop | Visible defeat reporting and result overlay reuse the application router; retry replaces all Match-scoped state with a fresh neutral Survival run; full suite is 1097 passed |
| 2026-08-22 | Added M10.3 neutral starting weapon | Shared weapon runtime now governs visible Survival fire/reload and snapshot state; temporary `DamageEnemy` command removed; full suite is 1098 passed |
| 2026-08-22 | Completed M10.3 neutral weapon integration | Pygame input emits world aim while reusable neutral ray targeting resolves the nearest valid hit deterministically; misses and hits share weapon operation; full suite is 1099 passed |
| 2026-08-22 | Completed M10.4 neutral kill rewards | Survival owns reward eligibility and wallet state; eligible first-lethal weapon kills award once, persist across waves, snapshot visibly, and reset on restart; full suite is 1100 passed |
| 2026-08-22 | Completed M10.5 neutral map collision movement | Shared Match actor movement now resolves authored geometry deterministically for Survival, Sandbox, and future modes while incomplete maps remain open; full suite is 1103 passed |

## Next Action

Begin M10.6 by defining coordinated neutral actor removal and using it to clean
defeated enemies between waves without losing death/reward facts or reusing IDs.
