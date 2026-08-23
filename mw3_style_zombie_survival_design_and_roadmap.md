# MW3-Style Zombie Survival Mode — Game Design & Implementation Roadmap

## Purpose of This Document

This document defines the target gameplay for the game: a **2D top-down zombie survival shooter inspired by the gameplay structure of Call of Duty: Modern Warfare 3 (2011) Special Ops Survival Mode**.

The goal is **not** to copy MW3's exact content, enemies, maps, weapons, names, or assets. The goal is to adapt the parts that made MW3 Survival compelling:

- endless escalating waves
- cash earned during a run
- short preparation periods between waves
- physical purchase stations around the map
- meaningful weapon progression
- armor, equipment, deployables, and support
- enemy types that create different tactical problems
- boss-like heavy enemies
- persistent rank/unlock progression outside the match
- map areas that have different gameplay purposes
- increasing difficulty through enemy combinations rather than only health scaling
- the feeling that the player's defensive plan eventually breaks down and must be changed

The current game already has a useful foundation:

- a top-down 2D world
- zombies
- player movement and combat
- melee/tool combat (Survival will use a pickaxe-like harvesting tool)
- a small number of purchasable weapons
- a large map
- collision / map work moving toward Tiled

The implementation should build on those systems incrementally instead of attempting a large rewrite.

---

# 1. Target Player Experience

The player should begin a run weak and gradually become more capable.

A typical run should feel like this:

1. Start with a pickaxe-like melee/harvesting tool and possibly a weak pistol.
2. Fight a small number of basic zombies.
3. Earn cash for kills.
4. Finish the wave.
5. Receive a short preparation period.
6. Run to physical stations around the map.
7. Buy a better weapon, ammunition, armor, or equipment.
8. Fight a more difficult wave.
9. Encounter new enemy types that invalidate simple strategies.
10. Gradually build a powerful survival loadout.
11. Eventually become overwhelmed by enemy combinations and increasing pressure.
12. Die and record the achieved wave / score / XP.
13. Use persistent XP to unlock additional equipment for future runs.

The primary goal is:

> Survive for as many waves as possible.

The game should not require a traditional level ending.

---

# 2. Core Gameplay Loop

The fundamental loop is:

```text
WAVE START
    ↓
Fight enemies
    ↓
Earn cash and XP
    ↓
Kill final enemy
    ↓
WAVE COMPLETE
    ↓
Preparation countdown
    ↓
Buy / reload / heal / reposition / place defenses
    ↓
NEXT WAVE
```

This rhythm is extremely important.

The game should alternate between:

```text
CHAOS
↓
RELIEF
↓
PREPARATION
↓
ANTICIPATION
↓
CHAOS
```

The preparation period prevents the game from becoming an uninterrupted stream of enemies and gives the player time to make meaningful decisions.

A reasonable initial preparation period is approximately **20–30 seconds**.

---

# 3. Economy

There should eventually be two separate progression currencies/systems.

## 3.1 Match Cash

Cash exists only during the current survival run.

The player earns cash from:

- kills
- headshots
- melee/tool kills
- special enemy kills
- boss kills
- possibly wave completion bonuses
- possibly optional challenges later

Example:

| Action | Example Reward |
|---|---:|
| Normal kill | $100 |
| Headshot | $125 |
| Risky melee/tool kill | $150 |
| Runner kill | $125 |
| Special zombie | $200–$400 |
| Brute / boss | $500+ |

Exact values should be balanced later.

Early design principle:

> Riskier or more skillful kills may reward slightly more money.

This keeps the equipped melee/tool option useful even after guns exist.

---

## 3.2 Persistent Survival XP

XP survives between runs.

XP should increase a persistent:

- Survival Level
- Survival Rank
- or similar progression system

Persistent progression should **unlock the ability to purchase equipment**.

It should generally not give the player powerful equipment for free.

Example:

```text
Rank 1
- starter pistol

Rank 3
- SMG

Rank 6
- shotgun

Rank 10
- assault rifle

Rank 15
- basic turret

Rank 20
- LMG

Rank 25
- survivor squad

Rank 30
- advanced armor

Rank 40
- explosive launcher
```

During the run, unlocked equipment still costs cash.

This creates two loops:

```text
RUN PROGRESSION
cash → purchases → survival

META PROGRESSION
XP → rank → new unlocks
```

Persistent progression should be implemented much later than the basic survival loop.

---

# 4. Starting Loadout

The player should begin weak.

Recommended eventual starting state:

```text
Pickaxe-like melee/harvesting tool
+
Weak pistol
+
Little or no armor
+
No deployables
+
No support
```

Zombie Survival's tool should remain important for both risky melee combat and
resource harvesting. The shared equipment role is configurable: another mode may
equip a knife, another tool, or no tool/melee item at all.

Early waves should be easy enough that experienced players can safely melee some enemies to conserve ammunition and gain bonus cash.

That creates an early risk/reward decision:

> Shoot safely, strike for more money, or preserve time to harvest resources?

---

# 5. Weapon Progression

The game does not need dozens of weapons.

Approximately **10–15 clearly differentiated weapons** is enough for a strong survival system.

Weapons should solve different combat problems rather than simply having larger damage numbers.

## Suggested Weapon Roles

### Starting

- Pickaxe-like tool (separate configurable tool/melee slot)
- Weak pistol

### Cheap Tier

- revolver or stronger pistol
- basic shotgun
- basic SMG

### Mid Tier

- assault rifle
- improved SMG
- pump shotgun
- semi-automatic rifle

### High Tier

- LMG
- automatic shotgun
- battle rifle
- heavy precision rifle

### Special / Utility

- grenade launcher
- flamethrower
- explosive crossbow or similar original weapon

Example roles:

| Weapon | Main Purpose |
|---|---|
| Pistol | cheap early survival |
| SMG | runners and mobility |
| Shotgun | close-range chokepoints |
| Assault rifle | general purpose |
| LMG | sustained horde control |
| Precision rifle | special / armored enemies |
| Flamethrower | crowd control |
| Explosive launcher | emergencies and clustered enemies |

Avoid designing every weapon as:

> old gun, but +20% damage.

The player should have reasons to prefer different weapons in different situations.

---

# 6. Physical Purchase Stations

Purchases should happen at physical stations located around the map rather than through one universal menu.

This makes movement and map knowledge meaningful.

A good long-term structure is three major categories.

## 6.1 Weapon Station

Possible location:

- central survivor hub
- armory
- warehouse
- gun shop equivalent

Purchases:

- weapons
- ammunition
- weapon upgrades through a separate, explicitly authored upgrade station

Weapon upgrades are mode-configured offers, not properties hardcoded into a
gun or Survival. Each offer targets a compatible owned weapon instance and can
apply a named, non-duplicated modification such as an extended magazine or an
SMG accuracy improvement (reduced spread). Future offers may adjust only
declared attributes such as magazine capacity, spread, recoil, damage, reload
time, or fire mode. The shared weapon system owns their effect; Survival owns
availability, price, and map placement.

---

## 6.2 Equipment Station

Possible location:

- construction checkpoint
- industrial yard
- junkyard

Purchases:

- grenades
- mines
- barricades
- barbed wire
- C4-like explosives
- turrets
- other deployable defenses

---

## 6.3 Medical / Support Station

Possible location:

- medical outpost
- radio tower
- central survivor base

Purchases:

- armor
- health
- self revive
- AI survivor support
- special support abilities

The stations should be spatially separated.

If every useful purchase is available from one safe room, the player has little reason to move around the map.

---

# 6.4 Harvesting and Barricade Construction

Zombie Survival should eventually start the player with a pickaxe-like tool in a
dedicated configurable tool/melee slot. It serves two capabilities:

- a close-range melee strike against damageable actors;
- a harvesting strike against compatible resource-bearing world objects.

Trees can yield wood and vehicles can yield metal. These are match-owned resources
used for barricade construction and repair rather than firearm ammunition or cash.
Exact yields, swing counts, and repair costs are balancing decisions for later.

The shared architecture must not assume every mode has a pickaxe. Equipment roles
are mode configuration:

```text
Zombie Survival: pickaxe-like tool with melee + harvest
Team Deathmatch: knife with melee only
Battle Royale: configured starting tool, lootable tool, or no tool
Other mode: no tool/melee slot if its rules do not need one
```

TMX will eventually author harvestable tree/vehicle placements and barricade build
anchors or permitted regions. Runtime systems own durability, yields, resource
inventory, construction transactions, barricade health/collision, repair,
destruction, and navigation updates. Map data supplies semantic definitions and
placement; it does not execute harvesting or building rules.

Initial construction should use authored anchors rather than unrestricted free
placement. This is easier to validate, keeps collision/navigation deterministic,
and lets map design control doors, windows, and chokepoints. Free placement can be
evaluated later if it materially improves play.

---

# 7. Armor

Armor should eventually be a major cash sink.

Suggested model:

```text
Health: 100
Armor: 100
```

Incoming damage consumes armor before health.

Armor should **not automatically regenerate**.

The player must purchase replacement armor between waves.

Example:

```text
Armor refill: $2,500
```

The exact value is not important yet.

The important part is the decision:

> Buy the expensive new weapon, or repair armor before the next wave?

That tension is central to the survival economy.

---

# 8. Self Revive

For solo play, long survival runs can become frustrating if one mistake instantly destroys a 45-minute run.

A self-revive purchase can soften that problem.

Example:

```text
Self Revive
Cost: $4,000
Uses: 1
```

Possible escalation:

```text
First purchase:  $4,000
Second purchase: $7,500
Third purchase: $12,000
```

This system should be added only after basic health, armor, and wave survival are working reliably.

---

# 9. Enemy Design Philosophy

The zombies do **not** need guns to reproduce the tactical structure of MW3 Survival.

Instead, each zombie type should represent a different **pressure role**.

The goal is to create enemies that invalidate specific player strategies.

---

# 10. Enemy Types

## 10.1 Walker

Basic zombie.

Characteristics:

- slow
- low or moderate health
- melee attack
- appears in large numbers

Purpose:

> baseline pressure

This is the first and only enemy needed for the earliest implementation phases.

---

## 10.2 Runner

Characteristics:

- fast movement
- lower health
- aggressive pursuit

Purpose:

> punish careless kiting and force fast target prioritization

Runners create pressure without needing ranged weapons.

---

## 10.3 Brute

The game's Juggernaut-like role.

Characteristics:

- very high health
- slower movement
- strong melee attacks
- visually distinctive
- difficult to stagger

Purpose:

> boss / heavy pressure / force repositioning

Example cadence:

```text
Wave 10
1 Brute

Wave 15
2 Brutes

Wave 20
3 Brutes
```

This can be adjusted later.

---

## 10.4 Spitter

Extremely important for preventing permanent camping.

Characteristics:

- maintains distance
- fires acid / toxic projectile / spit
- creates temporary hazardous areas

Purpose:

> anti-camping ranged pressure

The Spitter lets the game challenge a defensive position without giving zombies firearms.

---

## 10.5 Exploder

Characteristics:

- approaches player
- explodes near player or when killed
- damages player and possibly deployables

Purpose:

> punish tightly packed defenses and stationary play

---

## 10.6 Charger

Characteristics:

- heavy
- rush attack
- can break through weak barricades
- possibly knocks player backward

Purpose:

> defense breaker

---

## 10.7 Screamer

Characteristics:

- relatively weak itself
- dangerous support ability

Possible abilities:

- buff nearby zombie speed
- attract / summon reinforcements
- increase aggression
- temporarily disrupt turrets
- reduce player awareness

Purpose:

> priority target

---

## 10.8 Crawler

Characteristics:

- low profile
- difficult to notice
- possibly able to move below certain barriers

Purpose:

> bypass simple defensive layouts

---

# 11. Difficulty Scaling

Avoid making difficulty primarily:

```text
Wave 1 enemy: 100 HP
Wave 20 enemy: 2,000 HP
```

Some health scaling is acceptable, but the primary difficulty increase should come from:

- more enemies
- faster enemies
- mixed enemy types
- pressure from multiple directions
- special enemy combinations
- bosses
- anti-camping enemies
- defense-breaking enemies

Example progression:

```text
Wave 1
10 Walkers
```

```text
Wave 3
18 Walkers
3 Runners
```

```text
Wave 5
20 Walkers
8 Runners
```

```text
Wave 6
15 Walkers
2 Spitters
```

```text
Wave 8
25 Walkers
8 Runners
2 Spitters
1 Exploder
```

```text
Wave 10
1 Brute
10 Walkers
```

Later:

```text
Wave 20+
Walkers
Runners
Spitters
Exploders
Chargers
Multiple Brutes
```

The ideal experience is:

> The player finds a strategy that works, then future enemy compositions expose its weaknesses.

---

# 12. Boss / Heavy Waves

Certain waves should become recognizable milestones.

For example:

```text
Wave 10
Wave 15
Wave 20
Wave 25
Wave 30
...
```

Before one of these waves, the game may display:

```text
WARNING
HEAVY INFECTED INCOMING
```

Players should learn to anticipate these moments.

That creates preparation behavior:

> Wave 20 is next. I need armor, ammo, and explosives now.

---

# 13. Deployable Defenses

The game should eventually support limited tactical fortification.

This should **not** become a full base-building game.

Recommended deployables:

## Barricade

- blocks or slows a route
- zombies can damage it
- Chargers can destroy it more effectively

## Automatic Turret

- automatically targets zombies
- limited ammunition and/or health
- must be placed strategically

## Mine

- triggered by enemies
- area damage

## Barbed Wire

- slows enemies crossing it

## Fire Trap

- damages enemies entering an area

## Decoy

- temporarily attracts nearby enemies

The purpose is to let players augment existing map geometry rather than construct entire buildings.

---

# 14. AI Survivor Support

A future high-level system can adapt MW3's AI squad concept.

Example purchase:

```text
SURVIVOR TEAM
$8,000
```

Possible behavior:

- 2–3 armed NPC survivors
- follow player
- attack zombies
- use basic navigation
- can die
- persist until killed

Later version:

```text
HEAVY SURVIVOR TEAM
$15,000
```

Possible equipment:

- heavier armor
- shotguns
- LMG
- defensive positioning behavior

This is a late-phase feature.

Do not attempt it early.

AI ally pathfinding, combat targeting, state management, and balancing can introduce significant complexity.

---

# 15. Making the Map Matter

The map should not just be visual scenery.

Every major area should eventually have one or more gameplay reasons to visit it.

Possible assignments:

| Map Area | Possible Gameplay Purpose |
|---|---|
| Central survivor hub | weapon station |
| Gas station | ammo / explosives |
| Medical outpost | healing, armor, self revive |
| Radio tower | AI support / support abilities |
| Construction checkpoint | traps / barricades |
| Farm / greenhouse | healing items / temporary buffs |
| Junkyard | heavy gear / crafting |
| Warehouse | heavy weapons / ammunition |
| Park / campground | cheap early equipment |
| Swamp | dangerous shortcut / specialized enemy behavior |
| Collapsed highway | long-range defensive position |
| Residential block | temporary defensive buildings |

Not all of these must exist at first.

The important design principle is:

> The map should eventually give the player reasons to move between locations.

---

# 16. Areas Should Have Strengths and Weaknesses

There should not be one permanently optimal defensive position.

Example:

## Warehouse

Good against:

- Walkers
- Runners
- chokepoint waves

Bad against:

- Spitters
- Exploders
- Chargers

---

## Highway

Good against:

- Brutes
- ranged weapons
- long sightlines

Bad against:

- fast enemies attacking from multiple angles

---

## Residential Building

Good because:

- few entrances
- controllable lanes

Bad because:

- poor escape routes
- Exploders
- Chargers

---

## Open Central Area

Bad against:

- large standard hordes

Good against:

- bosses
- Spitters
- explosive enemies
- enemies requiring dodging space

The best place to fight should depend on the current threat.

---

# 17. What NOT to Add Too Early

Do not start with:

- dozens of weapons
- crafting
- attachment trees
- complicated perks
- AI survivor squads
- multiple boss classes
- elaborate persistent progression
- procedural loot
- large skill trees
- base building
- complex inventory systems
- advanced special effects
- multiple currencies
- multiplayer synchronization
- enemy elemental systems
- dynamic quests

Those features can hide whether the core survival loop is actually fun.

The first goal is not:

> Build the final game.

The first goal is:

> Prove that fighting waves, earning cash, buying something, and fighting a harder wave is fun.

---

# 18. Implementation Strategy

The project should be developed in small vertical steps.

Every phase should:

1. introduce only a small number of new concepts
2. be independently playable
3. be testable before starting the next phase
4. avoid unnecessary architecture for future features
5. preserve the existing game as much as practical
6. be small enough to give to an AI coding agent as a focused task

Do not ask an AI agent to:

> Implement the complete MW3-style survival system.

Instead, give it one narrowly scoped phase at a time.

---

# 19. Recommended Implementation Roadmap

---

# Phase 0 — Stabilize the Existing Game

## Goal

Make sure the current game has a stable baseline before adding survival systems.

Do not redesign gameplay yet.

## Verify

- player movement works
- configured tool/melee attack works (pickaxe-like tool in Survival)
- existing guns work
- zombies spawn
- zombies navigate to the player
- zombies damage the player
- zombies can die
- collisions work
- game can restart cleanly
- current weapon purchasing still works if already present

## Recommended Cleanup

Identify clear existing systems for:

- Player
- Enemy / Zombie
- Weapon
- Projectile
- Damage
- Game state
- Map
- Collision
- UI

Do not perform a massive architecture rewrite unless the current structure truly blocks the next phase.

## Completion Criteria

You can launch the game, fight zombies, die, and restart without obvious state bugs.

---

# Phase 1 — Basic Wave Manager

## Goal

Turn the current spawning system into explicit waves.

This is the first major survival feature.

## Implement

Create a WaveManager or equivalent system responsible for:

- current wave number
- number of enemies to spawn
- currently alive enemies
- whether a wave is active
- determining when the wave is complete
- starting the next wave

Initial wave formula can be extremely simple.

Example:

```text
Wave 1 = 5 zombies
Wave 2 = 7 zombies
Wave 3 = 9 zombies
Wave 4 = 11 zombies
```

or:

```python
enemy_count = 5 + (wave_number - 1) * 2
```

Do not worry about special enemies yet.

Use only basic Walkers.

## UI

Show:

```text
WAVE 1
ENEMIES: 5
```

## Completion Criteria

The player can:

1. start Wave 1
2. kill every zombie
3. see the game recognize the wave is complete
4. automatically start Wave 2
5. repeat indefinitely

No cash required yet.

---

# Phase 2 — Intermission / Preparation Timer

## Goal

Create the rhythm between combat and preparation.

## Implement

When the last enemy dies:

```text
WAVE COMPLETE
NEXT WAVE IN: 20
```

No enemies spawn during the countdown.

After the timer reaches zero, the next wave starts.

Suggested initial timer:

```text
20 seconds
```

## Important

Model game state explicitly.

For example:

```text
PREPARING
WAVE_ACTIVE
PLAYER_DEAD
```

Later there may be more states, but these are enough initially.

## Completion Criteria

The game reliably cycles:

```text
wave
→ complete
→ countdown
→ next wave
```

without overlapping spawns.

---

# Phase 3 — Cash for Kills

## Goal

Introduce the match economy.

## Implement

Player has:

```text
cash = 0
```

Basic zombie kill:

```text
+$100
```

Display current cash on the HUD.

Optional early bonus:

```text
Knife kill = +$150
```

Do not add complicated scoring yet.

## Completion Criteria

- every valid kill awards cash once
- duplicate cash cannot be awarded from the same zombie
- HUD updates correctly
- cash persists between waves
- cash resets when a new run starts

---

# Phase 4 — One Simple Weapon Purchase Station

## Goal

Prove the purchase loop works.

Do **not** create all three stations yet.

Create exactly one physical weapon station.

## Implement

When the player approaches the station:

```text
Press E to Open Weapon Station
```

Available items may initially be:

```text
Pistol Ammo
Shotgun
SMG
```

Example prices:

```text
Pistol Ammo  $250
Shotgun      $1,000
SMG          $1,500
```

The player cannot purchase without enough cash.

## Important

The store should use a data-driven item definition rather than hard-coding each purchase into the UI.

Example conceptual structure:

```python
{
    "id": "smg_basic",
    "name": "SMG",
    "price": 1500,
    "type": "weapon"
}
```

Exact architecture can match the existing codebase.

## Completion Criteria

The player can:

1. earn cash during a wave
2. finish the wave
3. run to the station
4. purchase a weapon
5. use that weapon next wave

At this point the game's core concept should already be testable.

---

# Phase 5 — Improve Wave Scaling

## Goal

Make the basic Walker-only game become gradually more difficult.

## Implement

Scale:

- enemy count
- spawn timing
- possibly very small health increases

Do not create special enemies yet.

Possible variables:

```text
total enemy count
max enemies alive simultaneously
spawn delay
walker speed
walker health
```

Avoid large HP inflation.

## Example

```text
Wave 1:  5 enemies
Wave 2:  8
Wave 3:  11
Wave 4:  14
Wave 5:  18
```

Later waves may also allow more zombies alive simultaneously.

## Completion Criteria

Waves feel increasingly dangerous even though every enemy is still the same type.

---

# Phase 6 — Weapon Expansion

## Goal

Create a small but meaningful weapon progression.

Do not build 15 weapons yet.

Target approximately:

```text
Knife
Pistol
SMG
Shotgun
Assault Rifle
LMG
```

Each should have a distinct purpose.

## Suggested Roles

```text
Knife
high risk / no ammo / bonus cash

Pistol
starter

SMG
high fire rate / mobile

Shotgun
close-range burst

Assault Rifle
general purpose

LMG
large magazine / sustained waves
```

## Completion Criteria

Players can make meaningful purchase choices rather than always buying one objectively superior gun.

---

# Phase 7 — Ammunition Economy

## Goal

Make weapons consume resources.

## Implement

Weapons should have:

- magazine ammo
- reserve ammo
- reload behavior
- ammo purchase cost

Ammo must not be so scarce that the game becomes tedious.

The purpose is to create decisions such as:

> Buy armor later, or refill the LMG now?

## Completion Criteria

Ammo matters during long waves and between-wave purchasing becomes more interesting.

---

# Phase 8 — First Special Enemy: Runner

## Goal

Introduce the first enemy that changes player behavior.

## Implement

Runner:

- faster than Walker
- less health or similar health
- melee attack
- visually distinguishable

WaveManager should support composition definitions.

Example:

```text
Wave 1
5 Walkers

Wave 3
8 Walkers
2 Runners
```

At this point, avoid embedding enemy selection directly in dozens of `if wave == X` statements if possible.

Create a composition structure that can later include more enemy types.

## Completion Criteria

Runners noticeably change target priority and movement behavior.

---

# Phase 9 — Armor

## Goal

Introduce the first major defensive cash sink.

## Implement

Player now has:

```text
health
armor
```

Damage is applied to armor first.

Armor does not regenerate automatically.

Add armor purchase to a simple station.

Possible initial implementation:

```text
Buy Full Armor
$2,000
```

## Completion Criteria

Players must decide between offensive and defensive purchases.

---

# Phase 10 — Second Purchase Station: Equipment / Medical

## Goal

Begin distributing gameplay systems around the map.

Create another physical station separate from the Weapon Station.

Initial options:

```text
Armor
Health refill
Grenades
```

Do not add turrets yet unless the grenade/equipment system already exists cleanly.

## Completion Criteria

The player has a reason to move to more than one area during intermission.

---

# Phase 11 — Brute Boss

## Goal

Add the first major milestone enemy.

## Implement

Brute:

- large health pool
- distinctive size / sprite
- strong attack
- slower than Runner
- high cash reward

Initially spawn one Brute on a predictable milestone:

```text
Wave 10
```

Display:

```text
WARNING
HEAVY INFECTED INCOMING
```

Do not initially combine Brutes with complicated special enemy groups.

## Completion Criteria

Wave 10 feels substantially different and forces the player to prepare.

---

# Phase 12 — Spitter

## Goal

Prevent the player from solving the game by camping permanently.

## Implement

Spitter should:

- stop at range
- fire a projectile
- target the player
- possibly create temporary hazard zones later

First version can simply fire a damaging projectile.

Add hazard pools only after ranged behavior works correctly.

## Completion Criteria

The player must sometimes leave a strong defensive position.

---

# Phase 13 — Wave Composition System

## Goal

Move from simple scaling toward intentional enemy combinations.

Create a system capable of describing waves using enemy groups.

Conceptual example:

```yaml
wave: 12
groups:
  - type: walker
    count: 20
  - type: runner
    count: 6
  - type: spitter
    count: 2
```

It does not have to use YAML. JSON, Python data, TMX properties, or another structure is fine.

The important part is that wave composition becomes data rather than scattered game logic.

## Completion Criteria

A designer can change wave composition without modifying enemy AI code.

---

# Phase 14 — Grenades and Basic Equipment

## Goal

Give the player tactical tools beyond guns.

Start with:

- grenade
- mine

Do not implement every equipment type at once.

## Completion Criteria

Equipment can be:

- purchased
- carried
- used
- limited
- replenished

---

# Phase 15 — Self Revive

## Goal

Protect long solo runs from ending on one mistake.

Implement:

- purchasable revive token
- one-time consumption
- downed / revive behavior or immediate revival equivalent

Keep the first implementation simple.

## Completion Criteria

A player can die once, consume the revive, continue the run, and later die normally if no revive remains.

---

# Phase 16 — Turret

## Goal

Add the first deployable defensive system.

The turret requires several systems:

- placement
- collision
- target detection
- target selection
- firing
- ammunition or durability
- zombie interaction

Because it touches many systems, it should not be added earlier.

First version:

- fixed position after placement
- rotates toward nearest valid zombie
- limited ammo
- no upgrading
- no repair system

## Completion Criteria

The turret is useful but cannot independently win waves.

---

# Phase 17 — Additional Enemy Types

Once the core game is stable, add special enemies one at a time.

Recommended order:

1. Exploder
2. Charger
3. Screamer
4. Crawler

Never add several simultaneously.

For each enemy:

1. implement behavior
2. test alone
3. integrate into a few waves
4. evaluate whether it actually creates a new tactical problem

If it does not change player decisions, redesign it.

---

# Phase 18 — Third Station / Support System

## Goal

Create a high-value support station.

Possible location:

- radio tower

Initial support could be one simple ability:

```text
Emergency Airstrike
```

or:

```text
Supply Drop
```

If the game setting does not support airstrikes, use a thematic equivalent.

Do not implement AI allies yet unless required.

## Completion Criteria

The player has a high-cost emergency purchase that can influence a difficult wave.

---

# Phase 19 — Map Role Pass

## Goal

Make major map locations mechanically meaningful.

Assign:

- purchase stations
- defensive areas
- dangerous shortcuts
- open boss-fighting areas
- chokepoints
- escape routes

Evaluate each major map zone with the question:

> Why would the player ever come here?

If the answer is "there is no reason," either:

- add a gameplay function
- redesign its geometry
- move a station there
- make it useful for specific enemy types
- remove unnecessary space

This should be done after the core survival systems exist, because then map decisions can be based on real gameplay.

---

# Phase 20 — Persistent XP and Unlocks

## Goal

Add long-term progression.

Do this only when the run itself is already fun.

Implement:

- XP earned per run
- rank
- unlock table
- save persistence

Example:

```text
Rank 1
Pistol

Rank 3
SMG

Rank 6
Shotgun

Rank 10
Assault Rifle

Rank 15
Turret

Rank 20
LMG
```

Unlocking an item only allows it to appear in a station.

The player must still buy it with match cash.

## Completion Criteria

A failed run still feels productive because XP contributes toward future unlocks.

---

# Phase 21 — AI Survivor Squad

## Goal

Add a late-game support purchase inspired by the squad concept in MW3 Survival.

Only attempt this when:

- enemy navigation is reliable
- ranged weapon behavior is reliable
- ally/enemy target filtering works
- player-follow AI is reliable

First version:

```text
2 armed survivors
follow player
shoot nearest zombie
can die
```

Avoid advanced cover behavior initially.

## Completion Criteria

AI allies feel like temporary combat support without requiring constant babysitting.

---

# Phase 22 — Advanced Balancing and High-Wave Design

At this stage, tune the full system.

Balance:

- cash income
- weapon prices
- armor prices
- ammo prices
- enemy counts
- boss frequency
- special enemy frequency
- intermission duration
- turret power
- support costs
- revive costs
- spawn locations

High waves should become difficult through combinations.

Example:

```text
Wave 25

30 Walkers
12 Runners
3 Spitters
2 Exploders
1 Charger
2 Brutes
```

The player should eventually lose because too many different tactical problems are happening simultaneously.

---

# 20. Recommended Milestones

The roadmap above can be grouped into larger milestones.

## Milestone A — The Survival Loop

Phases:

- 0
- 1
- 2
- 3
- 4

Result:

> Fight wave → earn cash → buy weapon → fight next wave.

If this is not fun, stop and adjust before adding complexity.

---

## Milestone B — Weapon Economy

Phases:

- 5
- 6
- 7

Result:

> Waves scale and the player has meaningful gun/ammo purchasing decisions.

---

## Milestone C — Tactical Survival

Phases:

- 8
- 9
- 10
- 11
- 12

Result:

> Different enemy types and armor begin forcing real tactical decisions.

---

## Milestone D — Equipment and Defense

Phases:

- 13
- 14
- 15
- 16
- 17

Result:

> Wave compositions, explosives, revives, turrets, and specialized enemies create the full survival combat loop.

---

## Milestone E — Map Systems

Phases:

- 18
- 19

Result:

> The map itself becomes part of the strategy.

---

## Milestone F — Long-Term Progression

Phases:

- 20
- 21
- 22

Result:

> Persistent unlocks, support squads, and high-wave balancing complete the long-term experience.

---

# 21. How to Use AI to Build This

Because AI will write much of the code, tasks should be intentionally narrow.

Bad request:

```text
Implement an MW3-style zombie survival mode with waves, shops,
armor, special enemies, turrets, persistent XP, and AI allies.
```

This invites:

- excessive refactoring
- invented architecture
- duplicated systems
- bugs across unrelated systems
- code that does not fit the existing project

Better request:

```text
Implement Phase 1 only: add a WaveManager to the existing game.

Requirements:
- Do not refactor unrelated systems.
- Reuse the existing zombie spawning system.
- Track current wave.
- Wave 1 spawns 5 zombies.
- Each following wave adds 2.
- The wave is complete when all spawned enemies are dead.
- Automatically begin the next wave.
- Display current wave and enemies remaining.
- Explain every file changed.
```

Then test it before asking for Phase 2.

---

# 22. Recommended AI Coding Workflow

For each phase:

## Step 1 — Give the AI the Current Architecture

Provide:

- important source files
- current game loop
- current enemy class
- current player class
- current weapon system
- relevant map / spawning code

Do not expect the AI to infer architecture from filenames alone.

---

## Step 2 — State the Exact Phase

Example:

```text
We are implementing Phase 3: cash for kills.
Do not implement later phases.
```

This prevents scope creep.

---

## Step 3 — Add Non-Goals

Example:

```text
Do not:
- add XP
- add shops
- change weapon balance
- add special enemies
- refactor the entire combat system
```

This is extremely useful with coding agents.

---

## Step 4 — Request Minimal Changes

Tell the AI:

```text
Prefer the smallest clean change that fits the current architecture.
Do not redesign unrelated systems.
```

---

## Step 5 — Require an Explanation

Ask it to provide:

- files changed
- why each file changed
- new state or classes introduced
- how the feature integrates with existing code
- how to test it

---

## Step 6 — Test Before Continuing

Do not immediately ask for the next phase.

Run the game.

Verify the completion criteria.

Fix bugs.

Commit the working state.

Then move to the next phase.

---

# 23. Git / Source Control Strategy

Create a commit after every working phase.

Example:

```text
phase-01-wave-manager
phase-02-wave-intermission
phase-03-kill-cash
phase-04-weapon-station
phase-05-wave-scaling
```

This makes AI-assisted development much safer.

If Phase 8 breaks the game, you can easily identify what changed.

For larger phases, use a feature branch.

Example:

```text
feature/survival-wave-manager
feature/armor-system
feature/spitter-enemy
feature/turret
```

---

# 24. Avoid Premature Generalization

AI coding tools often try to build generalized frameworks early.

For example, during Phase 1 it may propose:

- a generic event bus
- dynamic content registry
- plugin architecture
- complex dependency injection
- ECS conversion
- generalized AI state framework

Do not accept complexity solely because it may be useful someday.

Prefer:

> simple architecture that solves the current problem cleanly

until actual repetition demonstrates a need for abstraction.

---

# 25. Systems That Should Eventually Be Data Driven

Although premature abstraction should be avoided, several systems will naturally benefit from data definitions once they grow.

Eventually consider data-driven definitions for:

## Weapons

```text
id
name
price
damage
fire rate
magazine size
reserve ammo
reload time
movement modifier
unlock rank
```

## Enemies

```text
id
name
health
speed
damage
cash reward
XP reward
behavior type
```

## Store Items

```text
id
display name
price
category
unlock rank
```

## Waves

```text
wave number
enemy composition
spawn timing
boss flag
special message
```

Do this when multiple items exist, not before the first version works.

---

# 26. Suggested First Five AI Tasks

These are the first tasks that should actually be given to an AI coding agent.

## Task 1

**Implement explicit wave tracking.**

Only basic zombies.

Target:

```text
Wave 1 → 5 enemies
Wave 2 → 7
Wave 3 → 9
```

---

## Task 2

**Add a 20-second intermission after each completed wave.**

Show countdown UI.

No purchases required yet.

---

## Task 3

**Add match cash.**

Basic kill:

```text
+$100
```

Knife kill:

```text
+$150
```

Show cash on HUD.

---

## Task 4

**Add one physical weapon station.**

Sell:

```text
ammo
shotgun
SMG
```

Use existing weapon system.

---

## Task 5

**Improve Walker wave scaling.**

Increase counts and simultaneous enemy pressure.

Do not create special zombies yet.

After these five tasks, stop and play the game for a while.

The core design should already be visible.

---

# 27. First Playable Prototype Definition

The first meaningful prototype should contain only:

## Player

- movement
- health
- pickaxe-like tool/melee slot
- pistol
- shotgun
- SMG

## Enemy

- Walker only

## Systems

- waves
- enemies remaining
- intermission
- match cash
- weapon purchases
- ammunition purchases
- death
- restart

That is enough.

Do not wait for Brutes, turrets, or persistent XP before evaluating the concept.

The question at this point is:

> Is it satisfying to survive a wave, earn money, buy something better, and fight the next wave?

If yes, continue.

If no, fix the loop before adding features.

---

# 28. Second Prototype Definition

After the first prototype is proven:

## Player

- pickaxe-like tool/melee slot
- pistol
- SMG
- shotgun
- assault rifle
- LMG
- armor

## Enemies

- Walker
- Runner
- Brute
- Spitter

## Systems

- wave composition
- cash
- weapon station
- medical/equipment station
- ammo economy
- armor
- boss warnings

At this stage, the game should begin to strongly resemble the intended final survival experience.

---

# 29. Full Long-Term Vision

Eventually, a late-game run may feel like:

```text
Wave 1

The player knives basic zombies to build cash.
```

```text
Wave 4

The player buys an SMG.
Runners begin appearing.
```

```text
Wave 8

The player has an assault rifle.
Spitters force movement.
Armor becomes important.
```

```text
Wave 10

HEAVY INFECTED INCOMING.

The first Brute appears.
```

```text
Wave 15

The player has an LMG and turret.
Multiple special enemy types attack.
```

```text
Wave 20+

The player moves between defensive positions,
buys armor and ammunition,
uses mines and turrets,
fights multiple Brutes,
and adapts constantly.
```

Eventually:

```text
Turret ammunition is nearly empty.

Armor is broken.

A Spitter has made the current defensive position unsafe.

Runners are approaching from the side.

A Charger has destroyed a barricade.

Two Brutes are moving through the main lane.

The player has enough money for either ammo or armor,
but not both.
```

That is the desired end-state feeling.

The game should create escalating situations where:

> every system the player has built up is barely enough to keep the run alive.

Eventually the pressure becomes too great.

The run ends.

The player sees:

```text
SURVIVED TO WAVE 27
ZOMBIES KILLED: 684
CASH EARNED: $72,450
SURVIVAL XP: 8,420
```

Then the player wants to immediately try again.

---

# 30. Central Design Principle

The most important lesson from MW3 Survival is not the exact weapons, shops, or enemies.

It is this:

> The player finds a solution, and the game eventually introduces a new problem that makes that solution insufficient.

Examples:

```text
Walkers
→ player learns to kite
```

```text
Runners
→ kiting becomes harder
```

```text
Strong chokepoint
→ player camps
```

```text
Spitters
→ camping becomes unsafe
```

```text
Barricades
→ player fortifies
```

```text
Charger
→ barricades can be broken
```

```text
High-damage weapon
→ player dominates individual enemies
```

```text
Large mixed horde
→ ammunition and crowd control become problems
```

The objective is not simply to make enemies stronger.

The objective is to repeatedly force the player to **adapt**.

That should guide every future gameplay decision.
