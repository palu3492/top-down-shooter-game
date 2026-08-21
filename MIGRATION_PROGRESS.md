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
| Migration phase | Phase 0 — Baseline and decision record |
| Phase status | In progress |
| Active work package | M0.2 — Record current manual smoke path |
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
| 0 | Baseline and decision record | In progress | M0.1 complete: 869 tests pass; baseline failures recorded |
| 1 | Characterize the current vertical slice | Not started | — |
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

### M0.2 — Record current manual smoke path

**Status:** In progress

**Objective:** Define and execute the current end-to-end behavior path before the
rewrite so later integration checkpoints have a consistent manual reference.

**Scope:**

- Launch the current application through its supported entry point.
- Exercise menu entry, match start, movement, aiming, firing, reloading, weapon and
  equipment input, interaction/shop behavior, pause/resume, and match exit where
  the current build permits it.
- Record unavailable or intentionally disabled behavior rather than enabling or
  fixing it in this package.
- Capture enough evidence to distinguish a runtime failure from a stale automated
  expectation.

**Non-goals:**

- Fixing runtime problems found during the smoke path.
- Restoring disabled zombie spawning.
- Adding or changing automated tests.
- Moving or deleting legacy code.

**Acceptance criteria:**

- [ ] Smoke-path steps and observations recorded.
- [ ] Current application launchability recorded.
- [ ] Disabled or unavailable gameplay paths recorded.
- [ ] M0.3 selected as the next work package.

**Verification evidence:**

Pending.

## Phase 0 Work Packages

| ID | Work package | Status | Depends on |
|---|---|---|---|
| M0.1 | Establish automated baseline | Complete | — |
| M0.2 | Record current manual smoke path | In progress | M0.1 |
| M0.3 | Classify behavior: preserve, redesign, or delete | Not started | M0.1, M0.2 |
| M0.4 | Audit test intent and identify characterization gaps | Not started | M0.3 |
| M0.5 | Confirm Phase 0 exit evidence and open first ADRs only if needed | Not started | M0.4 |

## Verification Baseline

### Automated tests

| Date | Command | Result | Notes |
|---|---|---|---|
| 2026-08-21 | `uv run pytest` | 869 passed, 35 failed in 56.35s | 32 failures cascade from disabled zombie spawning; 3 independent failures recorded below |

### Static checks

| Date | Command | Result | Notes |
|---|---|---|---|
| 2026-08-21 | `uv run ruff check .` | 35 violations | 32 in untracked `tmp/tree-replacement/` scripts; 3 in tracked map tools |

### Manual smoke checks

| Date | Scenario | Result | Notes |
|---|---|---|---|
| — | Current pre-migration smoke path | Pending | Defined and executed in M0.2 |

## Behavior Classification

Behavior classification begins in M0.3. Entries must describe observable behavior,
not merely name a legacy class or file.

### Preserve

None recorded yet.

### Intentionally redesign

None recorded yet.

### Delete

None recorded yet.

## Temporary Adapters and Duplication

No migration adapters exist yet.

When one is introduced, record:

| Adapter | Why it exists | Introduced | Removal condition | Status |
|---|---|---|---|---|
| — | — | — | — | — |

## Known Failures and Risks

| ID | Type | Description | First observed | Blocks | Status |
|---|---|---|---|---|---|
| BASE-001 | Test configuration | 32 tests expect spawned zombies, but `config.ZOMBIE_SPAWNING_ENABLED` is intentionally `False`; wave, level, loot, movement, resolution, shop, scene, and session failures cascade from the empty groups | M0.1 | Clean test baseline | Recorded; do not fix in M0.1 |
| BASE-002 | Map/test drift | `test_world_obstacles_keep_their_tiled_geometry` expects a polygon obstacle, but the current `world_1.tmx` loader result contains none | M0.1 | Clean test baseline | Recorded; classify in M0.3 |
| BASE-003 | Legacy test drift | Instance-state test expects `Human` animation counters/type that the current `Human` no longer initializes | M0.1 | Clean test baseline | Recorded; likely obsolete under placeholder visuals, classify in M0.3 |
| BASE-004 | Timing/test behavior | Pause-loop test records 693 animation updates over 601 driven frames and fails its assertion that updates are fewer than frames | M0.1 | Clean test baseline | Recorded; investigate intent in M0.4 |
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

## Next Action

Execute and record M0.2, the current manual smoke path, without changing production
behavior.
