# Game Architecture and Migration Plan

## Status

This document defines the intended architecture for the game and the strategy for
migrating the current implementation toward it.

It is an architecture and migration plan, not a gameplay backlog. The initial
playable mode is Zombie Survival, whose design belongs in
`mw3_style_zombie_survival_design_and_roadmap.md`. Future modes may include online
Team Deathmatch and Battle Royale. Shared code must therefore describe general
shooter mechanics instead of assuming that every match contains one player,
zombies, waves, or cash.

This plan is incremental, but intermediate phases are allowed to leave the game
temporarily unplayable. Each phase must still produce verifiable code and converge
on explicit integration checkpoints. The rewrite must not become an unbounded
replacement effort with no testable path back to a working game.

## Confirmed Decisions

These decisions were confirmed before implementation began.

1. **Technology:** retain Python, pygame-ce, pytmx, and the current fixed-timestep
   desktop application during the migration. Changing engines is outside this
   rewrite unless separately approved.
2. **Networking:** treat online multiplayer as a first-class architectural
   constraint, but do not implement networking during the initial rewrite. The
   initial target remains a local, authoritative simulation.
3. **Compatibility:** preserve intended current behavior where it remains valuable,
   but remove accidental behavior, obsolete APIs, and save-file compatibility when
   they obstruct the new architecture.
4. **Initial mode:** Zombie Survival is the proving ground for shared mechanics.
   Survival-specific concepts must not be promoted into the shared game model just
   because it is the first mode.
5. **Intermediate playability:** individual migration phases do not need to leave
   the game playable. Automated verification remains mandatory, and designated
   integration checkpoints must restore a working end-to-end game.
6. **Development visuals:** use simple placeholder graphics for actors, enemies,
   weapons, projectiles, pickups, effects, and other gameplay objects during the
   rewrite. Polished asset creation and animation must not block mechanics work.
   Keep map design and the Tiled/TMX workflow as the intentional exception.
7. **Development HUD:** replace the graphical HUD with plain debug text during the
   rewrite. Health, armor, cash, equipped weapon, ammunition, equipment, match
   phase, wave status, timers, score, and other useful state should be readable
   without requiring HUD art or polished layout work.
8. **Maps:** continue authoring maps as Tiled `.tmx` files, while allowing the
   loader, schema, layers, properties, and runtime representation to change for the
   new architecture. Support multiple maps through shared contracts; no game system
   or mode may be structurally tied to the current map.
9. **Match selection:** game modes and compatible maps must be selectable at
   runtime. Leaving a match returns the player to an application flow where another
   mode and map can be selected and started without restarting the process. A
   switch disposes of the old match and constructs a fresh one; an active match is
   not mutated into a different mode or map.
10. **Role-based equipment:** firearm, tool/melee, throwable, deployable, and
    cargo roles are explicit configuration rather than one universal slot list.
    Zombie Survival initially equips a pickaxe-like tool that can both strike
    enemies and harvest authored objects. Other modes may configure a knife,
    another tool, or no tool/melee slot without changing shared combat,
    inventory, or input mechanisms.

## Product Direction

The project is a reusable top-down shooter platform with multiple game modes.
Zombie Survival is the first complete mode, not the definition of the platform.

The intended dependency direction is:

```text
Application shell
    scenes, menus, settings, process lifetime
                 |
                 v
Presentation and adapters
    pygame input, rendering, audio, assets, HUD, map adapter
                 |
                 v
Shared game simulation
    world, actors, movement, combat, inventory, teams, spawning, match state
                 ^
                 |
Game-mode rules
    Zombie Survival | Team Deathmatch | Battle Royale | future modes
```

The diagram shows dependency ownership rather than per-frame call order. A game
mode configures and directs the shared simulation through explicit contracts. It
must not reach into pygame rendering objects to make rule decisions.

## Architecture Principles

### 1. Mechanisms and policies are separate

A mechanism provides a reusable capability. A policy decides how a particular
mode uses it.

Examples:

| Mechanism | Mode policy |
|---|---|
| Find valid spawn locations | Spawn a zombie wave outside player sight |
| Apply damage and record attribution | Award Survival cash for a kill |
| Track match time and phase | Run a 25-second preparation phase |
| Represent teams and hostility | Zombies are hostile to all survivors |
| Create and remove actors | Respawn a TDM player after a delay |
| Place pickups in a world | Distribute Battle Royale loot at match start |

Mode code may compose mechanisms. Shared mechanisms must not import a concrete
mode.

### 2. Simulation and presentation are separate

Simulation state must not depend on `pygame.Surface`, fonts, audio devices, HUD
widgets, or camera offsets. Rendering observes simulation state. Audio and visual
effects react to state changes or domain events.

World coordinates are authoritative. Screen coordinates are calculated only by
the presentation layer.

### 3. Dependencies are explicit and narrow

Objects should receive the capabilities they need, not the complete game session.
A projectile needs motion, collision, ownership, and damage data; it does not need
the HUD, shop, wave system, or all global state.

Global mutable registries and direct reads of live input inside simulation systems
should be minimized. Configuration should be injected or captured in immutable
definitions at match creation where practical.

### 4. Composition is preferred over mode-specific inheritance

Actors share capabilities such as transforms, health, movement, inventories,
weapons, control, and presentation. Avoid duplicating those capabilities across
deep `Player`, `Zombie`, `Soldier`, and `Bot` hierarchies.

This does not require a full generic entity-component-system framework. Small,
plain state objects and focused systems are preferred until demonstrated needs
justify more machinery.

### 5. State changes have one owner

Health, ammunition, inventory, score, and match phase each need one authoritative
write path. UI and effects observe these values; they do not own or mutate them.

### 6. Determinism is a design constraint

Simulation uses a fixed timestep, controlled random-number generators, stable
entity identifiers, and explicit commands. Tests must be able to reproduce a match
from the same starting state and command sequence where practical.

This improves tests and replays now and reduces the cost of authoritative online
multiplayer later. Bit-for-bit determinism across operating systems is not an
initial requirement.

### 7. Build abstractions from demonstrated use cases

Zombie Survival provides the first real use case. A minimal developer sandbox or
second ruleset will test whether extracted mechanics are genuinely reusable.
Speculative frameworks for every possible future mode are out of scope.

## Current Architecture Assessment

### Foundations worth preserving

The current project already has several useful seams:

- A fixed-timestep simulation and separate render interpolation.
- A scene stack that owns application screens and pauses simulation cleanly.
- A `GameplayScene` whose lifetime owns one `Session`.
- A rules collaborator (`WaveSystem` / `LevelRules`) that begins to separate match
  outcomes and wave policy from the application shell.
- Weapon definitions separated from weapon-in-hand state.
- Basic item and backpack primitives without UI ownership.
- Tiled map loading and explicit world-coordinate helpers.
- A substantial test suite covering timing, weapons, waves, spawning, collision,
  shops, inventory, scenes, and outcomes.

These should be evolved rather than discarded without evidence.

### Primary architectural problems

#### `Session` is a god object

`shooter/session.py` currently owns or coordinates:

- input interpretation;
- player locomotion and camera movement;
- map loading and collision extraction;
- entity collections and lifecycle;
- player animation;
- weapon use and projectile creation;
- zombie AI, attacks, crowd separation, damage, death, and status effects;
- grenade and projectile simulation;
- loot generation and collection;
- shops and interaction;
- power-up effects;
- wave-rule advancement and outcomes;
- HUD, radar, notices, shop overlays, and world rendering.

This makes a second player, a different enemy faction, a headless test, or a
network-controlled match require changes in the same central class.

#### Combat targets concrete zombies

`Shot` and `Swing` update against `zombie_group` and directly call zombie health
methods. Explosions and melee follow separate damage paths. Damage attribution,
teams, friendly fire, assists, armor, damage types, and kill events therefore have
no shared home.

#### Actor state mixes simulation and pygame presentation

Player and zombie objects are pygame sprites containing health, animation frames,
collision rectangles, world position, and presentation state. Camera-relative
rectangles participate in gameplay collision. This complicates headless simulation,
multiple viewpoints, remote actors, and server authority.

#### Enemies own mode and economy assumptions

`Zombie` receives player cash and encodes zombie-specific health, movement,
spawning, animation, and reward behavior. A combat actor should not own the
recipient wallet or decide match rewards.

#### Spawning is split across constructors and wave rules

Zombie construction selects a random location around the current visible area,
while `WaveSystem` decides quantity and timing. This combines actor construction,
spawn-location selection, player visibility, and Survival policy.

#### Rules receive concrete UI and entity containers

Wave rules are constructed with a window, zombie sprite group, cash display model,
and visible rectangle. They directly create zombies and draw their own banners.
The existing rule seam is valuable, but its contract still crosses simulation,
presentation, and mode boundaries.

#### Model state lives in UI modules

Cash and grenade counts currently live in `shooter/ui/hud.py`. Shared simulation
state should not depend on its visualization.

#### Input is partly implicit

Most input arrives through scene/session methods, but wave skipping reads
`pygame.key.get_pressed()` directly inside rule simulation. A headless or remote
controller cannot reproduce that input through a normal command boundary.

#### World and camera ownership are coupled

The player is visually fixed near the screen center while camera movement acts as
player movement. Authoritative player position is consequently derived from camera
offset. This model does not extend cleanly to multiple local or remote actors and
should be migrated to explicit actor transforms with a camera that follows them.

## Target Concepts and Ownership

Names below describe responsibilities. Exact filenames may change during
implementation when tests reveal a better boundary.

### Application shell

Owns process lifetime, display setup, frame timing, settings, scene navigation,
pause behavior, and match creation. It knows which mode was selected but does not
implement that mode's rules.

The shell also owns the out-of-match flow:

```text
main menu
  -> mode selection
  -> compatible map selection
  -> match configuration
  -> active match
  -> result/leave match
  -> mode or map selection
```

Selections are explicit values passed into match creation. Exiting a match must
release its world, mode state, event queues, controllers, presentation bindings,
and transient resources so the next match cannot inherit state accidentally.

### Match

One running match owns:

- the simulation clock and current match phase;
- a `World` containing simulation entities;
- the selected `GameMode` rules object;
- seeded random sources;
- command ingestion;
- domain-event collection;
- match outcome and summary.

`Match.step(commands, dt)` is the conceptual simulation entry point. It does not
draw and does not poll pygame.

### World

Owns entity registration, stable entity IDs, spatial queries, collision geometry,
and lifecycle queues. Creation and removal occur at controlled points so systems do
not invalidate each other while iterating.

The world exposes queries by capability or relationship, not collections named
`zombies`.

### Actors

An actor is a simulation participant with a stable ID and selected capabilities:

- transform and collision shape;
- health and optional armor;
- faction/team membership;
- locomotion state;
- inventory/loadout;
- weapon-user state;
- optional controller or AI state.

Player ownership, AI control, and network ownership are separate from the actor's
combat capabilities.

### Commands and controllers

Controllers translate input or AI decisions into commands such as:

- move in a direction;
- aim at a world position;
- begin or stop firing;
- reload;
- switch equipment;
- interact;
- request a mode-specific action such as skipping preparation.

Pygame input, bots, replay playback, and future network clients should all reach the
simulation through the same conceptual command boundary.

### Combat

The shared combat model owns:

- weapon definitions and equipped weapon state;
- immutable weapon-upgrade definitions and per-instance owned modifications;
- fire cadence, reload state, magazines, and reserves;
- hitscan and projectile attacks;
- collision and impact resolution;
- damage requests and results;
- health, armor, death, and status effects;
- source, instigator, weapon, team, and damage-type attribution.

A representative damage request may contain:

```text
source entity | instigator entity | target entity | amount
weapon id | damage type | impact position | simulation tick
```

Combat emits facts such as `DamageApplied`, `ActorDowned`, and `ActorKilled`.
Zombie Survival may listen to a kill and award cash. Team Deathmatch may increment a
team score. The combat system does neither itself.

### Teams and relationships

Every damageable actor can have a faction/team identity. A relationship policy
answers questions such as hostile, friendly, neutral, and whether damage is
permitted. Do not encode foundational checks as `is_zombie`.

This must support at least:

- one survivor faction versus one enemy faction;
- two or more player teams;
- free-for-all participants;
- neutral or environmental actors;
- configurable friendly fire.

### Spawning

Shared spawning is split into three responsibilities:

1. **Spawn definitions:** authored map markers, regions, tags, weights, and
   constraints.
2. **Spawn selection:** choose a valid location using geometry, occupancy,
   visibility, team safety, distance, and a controlled random source.
3. **Mode policy:** decide which actor to spawn, when, and with which selection
   constraints.

Creating an actor must not itself select a random world position.

### Maps and interaction

The map adapter converts Tiled data into simulation-level map data:

- collision geometry;
- world boundaries and traversal limits;
- named regions and navigation data;
- tagged spawn points;
- interaction points;
- authored object placements and destructible-object definitions;
- authored harvestable placements, resource-yield metadata, and construction
  anchors or permitted build regions;
- map metadata;
- presentation layers and asset references.

Tiled `.tmx` maps remain part of the target architecture rather than a legacy
system to replace. Map layout, collision, authored regions, spawn markers, and
interaction markers should continue to be created in Tiled. The adapter must keep
Tiled-specific objects at the boundary so the simulation consumes neutral map
data without parsing TMX details throughout gameplay code.

The current map is one data instance, not a global world definition. A map catalog
or match configuration selects a map by stable ID and supplies it to match creation.
Shared systems and modes must not hardcode a TMX path, layer object, landmark,
coordinate, world size, spawn location, shop location, or collision shape from a
particular map.

Maps are expected to share a reusable authored vocabulary. The exact schema should
be documented and validated, and may include:

- map identity, display name, version, bounds, and supported modes;
- visual tile/object layers and collision geometry;
- explicit world boundaries, playable areas, and out-of-bounds behavior;
- navigation regions, blockers, costs, or connectivity metadata;
- tagged spawn points and spawn regions with faction/mode/role constraints;
- tagged interaction anchors for gun-buy boxes, stations, doors, loot, objectives,
  or hazards;
- destructible object placements with stable definition IDs, initial state, and
  optional mode-specific tags;
- harvestable definitions with stable resource IDs, durability, compatible tool
  tags, and yield policy inputs;
- construction anchors/regions with recipe or placement tags for temporary
  barricades and other mode-created world objects;
- named tactical regions and semantic tags such as indoor, outdoor, high ground,
  chokepoint, or restricted;
- optional camera, audio, lighting, and presentation metadata.

Not every map must contain every optional element. A map declares its capabilities,
and a selected mode validates its required elements before the match starts. For
example, Zombie Survival may require valid survivor and enemy spawn regions while a
future Team Deathmatch map may require compatible team spawn sets.

The current TMX map is intentionally incomplete and must not be treated as the
canonical or final schema. Schema adoption is progressive: missing future layers
such as boundaries, complete collision, destructibles, spawn sets, or gun-buy
locations are valid during migration unless the selected mode explicitly requires
them. New semantic object types should extend the neutral map model and adapter,
not introduce map-specific parsing or gameplay branches.

TMX architecture may change as needed: layer names can be standardized, custom
properties introduced, legacy objects migrated, tilesets reorganized, and the map
adapter rewritten. The durable contract is that map authors continue working in
Tiled and gameplay receives a validated, map-neutral runtime model.

The map catalog exposes metadata needed by selection UI without loading a complete
match. It supports filtering maps by the selected mode's requirements and reports
why an incompatible map cannot be selected.

Interaction uses general interactable contracts. A Survival weapon station, a
Battle Royale loot container, and a door can share detection and command handling
without sharing purchase rules.

### Inventory, equipment, and economy

Items, stacks, inventories, loadouts, weapons, ammunition, and equipment are
shared. Currencies and shops are reusable mechanisms, but the existence, lifetime,
prices, rewards, and stock are mode policy.

Match cash belongs to Zombie Survival match state. Persistent progression belongs
outside the live match. Neither belongs in the HUD.

Equipment roles are configured per mode. A loadout may contain firearm slots,
an optional tool/melee slot, throwable/equipment slots, deployables, and stackable
cargo without treating them as interchangeable. Zombie Survival's initial
tool/melee definition is a pickaxe-like tool with both melee-attack and harvesting
capabilities. A Team Deathmatch ruleset may substitute a knife, and another mode
may omit that role entirely. Shared code dispatches explicit capabilities such as
`melee_attack`, `harvest`, `repair`, or `build`; it does not branch on the names
`pickaxe`, `knife`, `tree`, or `vehicle`.

Harvested wood and metal are match-owned resource inventory values. Harvestable
durability/yield, construction recipes, transactional resource spending,
barricade creation/repair/destruction, collision, and navigation invalidation are
separate reusable mechanisms. Zombie Survival decides which resources, recipes,
build phases, and rewards are enabled.

### Presentation

Presentation consumes read-only simulation snapshots and domain events to provide:

- visual bindings, using placeholder shapes initially and sprites/animation later;
- camera transforms;
- HUD and mode overlays;
- radar/minimap views;
- particles and temporary visual effects;
- sound and music.

Presentation may interpolate between simulation states. It must not resolve hits,
apply damage, award currency, or advance match phases.

### Placeholder visual strategy

During architecture and mechanics development, presentation should favor a small,
consistent debug vocabulary over production art:

- colored circles or rectangles for actors and enemy archetypes;
- lines, wedges, or simple shapes for aim, melee reach, and projectiles;
- labeled blocks or icons for weapons, equipment, pickups, and interactables;
- simple flashes and areas for damage, explosions, and status effects;
- optional debug overlays for entity IDs, factions, health, collision, navigation,
  spawn regions, and authoritative world positions.

The development HUD is a text-only diagnostic view. It should show only information
that exists in read-only shared or mode-specific state, including as appropriate:

- player ID, faction/team, health, armor, and life state;
- equipped weapon, magazine, reserve ammunition, reload, and cooldown state;
- carried equipment and relevant inventory counts;
- Survival cash and purchase feedback;
- match mode, phase, elapsed/remaining time, wave, enemies remaining, and outcome;
- optional simulation tick, frame timing, entity counts, seed, and spawn diagnostics.

The debug HUD may use simple alignment, colors, and panels for readability, but it
should use text and basic pygame primitives rather than illustrated HUD assets. It
must not become an authoritative owner of health, cash, ammunition, wave state, or
any other gameplay value.

Placeholder visuals should be driven by the same read-only simulation state and
events that will eventually drive finished presentation. They are not permitted to
become simulation state themselves. Existing finished assets may remain where they
work without maintenance, but migration work should not depend on preserving their
animation or binding APIs.

The map is the exception: the Tiled/TMX map, its collision and metadata, and useful
existing map artwork remain visible so movement, sight lines, chokepoints, spawning,
and interactions can be evaluated in their real spatial context.

### Game-mode contract

The initial contract should be intentionally small and grow through proven needs.
Conceptually, a mode must be able to:

- configure a new match and its factions;
- react to match start and simulation events;
- advance its phase/rules state;
- request spawns through shared services;
- determine whether the match has ended;
- expose a read-only mode status for UI;
- produce a match result/summary.

The contract should not receive a window, draw a banner, poll input, mutate pygame
groups, or instantiate concrete sprites.

Modes are registered in a mode catalog with stable IDs and selection metadata.
Selecting a mode creates a new rules instance for one match; mode instances and
their mutable state are never reused across matches. The catalog and mode contract
expose enough requirements to determine compatible maps before match construction.

### Zombie Survival mode

Zombie Survival owns:

- wave composition and scheduling;
- preparation phases and skip policy;
- zombie archetype selection;
- survival spawn constraints;
- match cash and reward policy;
- Survival shops and available support;
- boss-wave scheduling;
- endless difficulty escalation;
- Survival scoring, HUD status, and outcomes.

Zombie AI implementations may live near the mode initially, but generic steering,
navigation, targeting, and weapon use should move into shared systems when a second
actor type demonstrates reuse.

## Provisional Package Direction

The final tree should emerge incrementally. The following is a responsibility map,
not permission for an empty-framework rewrite:

```text
shooter/
  app/                 process, loop, scenes, settings, match creation
  simulation/
    match.py           authoritative match step and lifecycle
    world.py           entity IDs, lifecycle, spatial/world queries
    commands.py        player, AI, replay, and network command model
    events.py          domain-event definitions and queue
    actors/            actor state and reusable capabilities
    combat/            weapons, projectiles, damage, health, armor
    inventory/         items, stacks, loadouts, equipment
    teams.py           affiliation and relationship policy
    spawning/          spawn definitions, selection, validation
    maps/              map catalog, validation, runtime model, and Tiled adapter
    interaction/       interactables and interaction resolution
  modes/
    zombie_survival/   waves, preparation, rewards, shops, enemy composition
    sandbox/           minimal architecture/test mode
  presentation/
    pygame/            renderer, animation, audio, input adapter, assets
    ui/                shared HUD plus mode-specific views
```

Existing modules should move only when their responsibility has actually been
separated. Compatibility adapters are acceptable during migration and should be
deleted when their callers are gone.

## Migration Strategy

### Rules for every phase

Every migration phase must:

- begin with tests or a reproducible observation of behavior being retained;
- define which automated or focused manual checks can verify its output even when
  the full application is temporarily unavailable;
- avoid combining a behavior redesign with a structural move unless required;
- provide a temporary adapter when old and new code need to coexist;
- remove superseded code once no production caller uses it;
- end with tests and lint, plus a focused manual check when the affected path is
  runnable;
- update this document when an architectural decision changes.

No phase is complete merely because new types exist. Production gameplay must use
the new boundary by the next designated integration checkpoint.

The planned integration checkpoints are after Phase 4 (shared damage pipeline),
Phase 7 (neutral match and real mode boundary), and Phase 9 (reuse proven by the
sandbox). If an earlier phase intentionally breaks application startup, its work
must be integrated and the game restored at the next checkpoint.

### Phase 0: Baseline and decision record

**Goal:** establish a trustworthy starting point before behavior moves.

Work:

- Run the full automated suite and record any known failures.
- Record a short manual smoke path: launch, start a match, move, fire, reload,
  change weapons, throw equipment, kill enemies, finish a wave, buy, pause, lose,
  and return to the menu.
- Identify tests that assert accidental implementation details instead of behavior.
- Add a lightweight architecture decision record format under `docs/decisions/` only
  when the first lasting decision needs one.

Exit criteria:

- The existing baseline is green or known failures are documented.
- The manual smoke path is repeatable.
- Open product/technology decisions that block Phase 1 are resolved.

### Phase 1: Characterize the current vertical slice

**Goal:** protect the intended shooter loop while internals change.

Work:

- Add focused integration tests around command-to-outcome behavior: firing consumes
  ammo, impacts cause damage, kills remove actors, reloading restores the magazine,
  invalid targets are ignored, and a cleared wave enters preparation.
- Add deterministic test helpers with an injected random seed/source.
- Separate tests of pure rules from tests requiring pygame surfaces or sprites.
- Mark behavior intentionally scheduled for redesign rather than freezing it by
  accident.

Exit criteria:

- Core combat and match-flow behavior can be verified without relying only on
  screenshots or long end-to-end sessions.
- Random spawn/combat tests can be reproduced from a seed.

### Phase 2: Introduce neutral commands, events, and IDs

**Goal:** create the narrow communication vocabulary needed by later extraction.

Work:

- Introduce stable entity IDs independent of pygame sprite identity.
- Introduce command values for movement, aim, fire, reload, equipment selection,
  and interaction.
- Adapt pygame input into commands before simulation code sees it.
- Introduce a small domain-event queue for combat and lifecycle facts.
- Replace direct wave-skip polling with an explicit mode command.
- Do not yet build a generic event bus or networking transport.

Exit criteria:

- Gameplay simulation no longer polls pygame keyboard state directly.
- Tests can drive essential player actions with commands.
- Important lifecycle facts can be observed without inspecting UI state.

### Phase 3: Extract authoritative actor state and world position

**Goal:** stop using camera movement and sprite rectangles as authoritative actor
state.

Work:

- Introduce simulation transforms and collision shapes in world coordinates.
- Make player movement update the player transform.
- Make the camera follow the local player through a presentation adapter.
- Separate simulation collision bounds from animation image rectangles.
- Introduce controlled world entity registration and removal.
- Replace or retain pygame sprites only as presentation adapters; prefer simple
  placeholder shapes when existing asset or animation bindings slow the migration.
- Replace the hardcoded current-map path with an explicit map definition supplied
  when creating a world or match, without requiring a full multi-map menu yet.

Exit criteria:

- The player and all combat actors have explicit world positions.
- Camera changes cannot change simulation outcomes.
- Two actors can be represented simultaneously without either being defined as the
  screen center.
- Headless tests can advance actor movement and collision without loading animation
  frames.
- World creation is parameterized by map data rather than a module-level TMX path.

### Phase 4: Unify health, damage, death, and attribution

**Goal:** create one reusable combat consequence pipeline.

Work:

- Extract shared health and optional armor state.
- Introduce a damage request/result model with instigator, source, weapon, type,
  target, amount, and tick.
- Route bullets, melee, explosions, contact attacks, and power effects through the
  same damage service where their semantics overlap.
- Apply team/relationship rules before damage.
- Emit damage, death, and kill events.
- Move rewards and loot consequences out of enemy objects and projectile code.
- Preserve distinctions between killed, despawned, expired, and removed.

Exit criteria:

- Projectiles and melee target damageable actors, not a zombie group.
- Zombie instances do not receive or mutate the player's cash.
- Survival rewards and drops react to attributed events.
- Friendly-fire behavior is testable through relationship policy.

### Phase 5: Extract weapon operation and inventory integration

**Goal:** make weapons reusable by local players, bots, remote players, and future
enemy types.

Work:

- Keep immutable weapon definitions separate from per-instance runtime state.
- Move fire, reload, cooldown, ammo consumption, spread, and attack creation behind
  combat commands/services.
- Use injected random sources for spread.
- Reconcile carried weapons, ammunition, equipment, and the existing backpack into
  one explicit loadout/inventory model.
- Keep animation and audio as reactions to weapon events.

Exit criteria:

- A controller requests fire; it does not directly create a pygame projectile.
- A non-player-controlled actor can use the same weapon runtime contract.
- Weapon tests do not require a HUD or zombie instance.

### Phase 6: Extract spawning

**Goal:** make spawn mechanics reusable and leave timing/composition to modes.

Work:

- Parse tagged spawn points and regions from map data.
- Define and validate the common TMX metadata used by spawning and interaction.
- Add capability-based validation so incomplete maps report missing mode
  requirements without forcing unrelated optional layers to exist.
- Introduce spawn queries and constraints for visibility, distance, occupancy,
  collision, faction, and tags.
- Move random position choice out of `Zombie.__init__`.
- Give actor factories explicit definitions and positions.
- Change Survival waves to request actor spawns through the shared service.

Exit criteria:

- Constructing an actor has no random placement side effect.
- Spawn selection is testable with synthetic maps and seeded randomness.
- The same service can express Survival perimeter spawning and team spawn selection.
- At least two small map fixtures can exercise the same loader and spawning
  contracts without map-specific Python branches.

### Phase 7: Establish `Match` and the real game-mode boundary

**Goal:** make Zombie Survival one rules package hosted by a neutral match.

Work:

- Introduce the authoritative `Match` owner around the extracted world and systems.
- Select maps through match configuration/catalog data and validate mode-map
  compatibility before simulation begins.
- Introduce mode and map catalogs with stable IDs and lightweight selection
  metadata.
- Add the application flow needed to leave a match, return to selection, and start
  a different compatible mode/map combination without restarting the process.
- Ensure match disposal removes all match-scoped simulation and presentation state.
- Replace the current rules constructor signature with a narrow mode contract.
- Move wave count, preparation timing, Survival cash, shops, rewards, and Survival
  outcome policy under `modes/zombie_survival/`.
- Expose a read-only mode-status model for the Survival HUD.
- Move countdown drawing out of wave rules.
- Retain `GameplayScene` as the application/presentation owner of one match.

Exit criteria:

- Shared simulation code contains no wave, zombie, preparation, or Survival-cash
  assumptions.
- Mode rules do not import pygame UI/rendering modules.
- Starting a game selects a mode configuration and constructs a neutral match.
- A mode can run on any map satisfying its declared requirements without importing
  or branching on that map's identity.
- Consecutive matches using different mode/map configurations do not leak actors,
  scores, cash, timers, commands, events, camera state, or presentation bindings.

### Phase 8: Separate presentation completely

**Goal:** make the simulation runnable without a display or audio device.

Work:

- Create presentation bindings from entity state/type to placeholder shapes, with
  an interface that can later select sprites and animation without changing the
  simulation.
- Render from snapshots/read-only views rather than mutable simulation objects.
- Replace the graphical HUD with a text-based debug overlay and move radar, health,
  armor, weapon, ammo, cash, match phase, wave state, and mode banners to read-only
  view models.
- Trigger placeholder flashes, optional sounds, particles, and transient animations
  from events where they materially help mechanics testing.
- Remove simulation imports of assets, audio, fonts, surfaces, and UI classes.

Exit criteria:

- A headless match can be created and advanced without loading pygame assets.
- Rendering may be replaced or disabled without changing match logic.
- UI contains no authoritative game state.

### Phase 9: Prove reuse with a sandbox ruleset

**Goal:** demonstrate that the boundaries support more than Zombie Survival before
building a full second product mode.

Work:

- Add a minimal developer sandbox with two factions or actors.
- Reuse movement, commands, weapons, damage, teams, spawning, death, and outcomes.
- Exclude waves, Survival cash, Survival shops, and zombie-specific win logic.
- Record architectural changes required by the second use case.

Exit criteria:

- The sandbox is playable or fully simulatable through the normal match host.
- It does not branch shared mechanics on a zombie/survival flag.
- Shared abstractions made unnecessary by both real use cases are removed.

### Phase 10: Resume Zombie Survival feature development

**Goal:** build the MW3-inspired Survival loop on the stable shared mechanics.

Initial product milestone:

- explicit active-wave and preparation phases;
- predictable kill rewards;
- one physical weapon/ammunition station;
- a deliberately tuned first five waves;
- several distinct enemy roles using shared actor/combat/spawn systems;
- clear mode-specific HUD state and outcomes.

Subsequent Survival product packages include:

- a configurable tool/melee role, with Survival starting with a pickaxe-like
  tool while other modes may select a knife or none;
- TMX-authored harvestable trees, vehicles, and future resource-bearing props;
- match-owned wood/metal inventory and deterministic yield rules;
- authored construction anchors/regions and transactional barricade recipes;
- barricade health, repair, destruction, collision, enemy targeting, and dynamic
  navigation response.

Detailed design and balancing remain in the Survival roadmap.

## Networking Readiness Without Networking Now

Future online modes change the authority model substantially. The rewrite should
preserve the following options without implementing sockets, matchmaking, lobbies,
rollback, or prediction yet:

- Commands are serializable values rather than pygame events.
- Entity identities are stable and not process-memory identities.
- Simulation time is tick-based/fixed-step.
- Random sources are owned, seeded, and not hidden behind module-level `random`.
- Match state can eventually produce snapshots or deltas without serializing
  surfaces, sounds, or callbacks.
- The server can eventually be authoritative for movement, firing, hits, damage,
  inventory, spawning, scoring, and outcomes.
- Local presentation can interpolate independently from authoritative state.
- Player/controller ownership is data, not assumed from a singleton human.

Networking code should begin only when a small local match boundary exists and its
commands and state can be serialized in tests. Battle Royale scale must not be
assumed feasible merely because these boundaries exist; player count, bandwidth,
interest management, map size, hosting, cheating, and persistence will require a
separate feasibility plan.

## Testing Strategy

Tests should be organized by purpose rather than by how much pygame they happen to
touch.

### Pure unit tests

- weapon and item definitions;
- health, armor, and damage rules;
- team relationships;
- inventory operations;
- spawn constraint evaluation;
- mode phase transitions and scoring;
- deterministic random choices.

### Simulation integration tests

- commands advance actors;
- firing creates attacks and consumes ammunition;
- impacts produce attributed damage and death events;
- modes react to events without combat knowing the mode;
- spawn requests produce valid actors;
- match outcomes and summaries are correct.

### Adapter tests

- pygame events produce expected commands;
- Tiled data produces the expected simulation map;
- simulation state selects the correct presentation binding;
- HUD view models reflect match and mode status.

### End-to-end smoke tests

- application boot and scene transitions;
- start, play, pause, resume, lose/win, and return;
- start one mode/map combination, leave it, select another compatible combination,
  and start again without restarting the application;
- resize/fullscreen and asset loading;
- one representative Survival wave/purchase loop.

Architecture tests or import-boundary checks may be added once packages stabilize.
They should prevent concrete dependency regressions, not dictate a speculative tree.

## Quality Gates

A migrated system is accepted when:

- its authoritative state has a clear owner;
- its rules can be tested without rendering where appropriate;
- it does not import a concrete mode from shared simulation code;
- its random behavior can be controlled in tests;
- it communicates through commands, state, focused services, or domain events;
- old production paths have been removed;
- existing intended behavior remains covered;
- the full application is playable when the phase is a designated integration
  checkpoint.

Recommended continuous checks:

```text
uv run pytest
uv run ruff check .
manual smoke path for behavior changed by the phase
```

## Explicit Non-Goals

The initial rewrite does not include:

- implementing online multiplayer;
- committing to a Battle Royale player count or backend architecture;
- changing the engine or programming language;
- building a general-purpose game engine or full ECS framework;
- adding new Survival content merely to exercise unfinished abstractions;
- preserving every legacy class, import path, or accidental behavior;
- rewriting working systems only to match a preferred folder structure;
- balancing the complete weapon roster or long-term wave curve;
- implementing persistent accounts, ranks, matchmaking, or anti-cheat;
- producing or polishing final actor, enemy, weapon, projectile, pickup, or effect
  artwork during the migration;
- preserving or producing a polished graphical HUD during the migration;
- replacing the Tiled/TMX map-authoring workflow;
- building gameplay systems around hardcoded assumptions from the current map.

## Risks and Controls

| Risk | Control |
|---|---|
| Rewrite stalls gameplay work indefinitely | Use bounded phases, automated evidence, and mandatory integration checkpoints |
| Generic abstractions become more complex than the game | Require Zombie Survival plus a sandbox use case |
| Tests freeze legacy mistakes | Label intended behavior and scheduled redesigns separately |
| Old and new paths coexist forever | Track adapters and delete each when its callers are migrated |
| Networking goals cause premature distributed-system work | Preserve serializable boundaries but defer transport/backend work |
| Mode logic leaks into shared systems | Enforce dependency direction and event-based consequences |
| Presentation remains authoritative through pygame sprites | Move transforms, collisions, and health into headless state first |
| Refactors silently change game feel | Use repeatable manual smoke paths alongside automated tests |

## Working Method and Documentation

- This file is the source of truth for architecture and migration order.
- The Survival roadmap is the source of truth for Zombie Survival experience,
  content, and balancing.
- While the migration is active, this document's Phases 0-9 take precedence over
  similarly named implementation phases in the Survival roadmap. The Survival
  roadmap resumes as the product backlog at Phase 10 here.
- Small implementation tickets should reference one migration phase and state the
  behavior they preserve or intentionally change.
- Lasting decisions that replace a reasonable alternative should be recorded as a
  short architecture decision record once implementation begins.
- Update the current assessment as legacy responsibilities are removed; do not let
  this document become a historical description mistaken for current code.

## First Implementation Slice After Approval

Do not begin by creating the entire provisional package tree. Begin with Phase 0
and Phase 1, then take the smallest production slice through the new boundaries:

```text
pygame fire input
  -> explicit Fire command
  -> weapon runtime validates and consumes ammunition
  -> attack/projectile carries actor and weapon attribution
  -> shared damage service resolves impact
  -> ActorKilled event
  -> Zombie Survival awards cash and loot
  -> HUD observes the resulting state
```

This slice crosses the most important reusable mechanics and exposes false
boundaries early. Once it works in production and tests, movement/world position and
the remaining combat paths can migrate using the same vocabulary.
