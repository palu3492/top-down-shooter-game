# Asset Art Direction and Migration Specification

Status: production proposal for the HD asset migration  
Applies to: gameplay art, UI art, menu art, effects, icons, and audio references  
Does not change: gameplay collision, movement, damage, reach, or spawn rules

## 1. Goal

Replace the current mixed-resolution asset collection with a cohesive, higher-fidelity 2D presentation while making later additions routine. Artwork must be replaceable without requiring entity code to know filenames, frame counts, source dimensions, or alignment offsets.

The target is **stylized gritty illustration**, viewed from directly above with a slight three-quarter reveal of character surfaces. It should read immediately at the game's 1080x720 logical resolution, retain strong silhouettes under rotation, and avoid photorealistic detail that disappears during play.

This is not a resolution-only upgrade. Acceptance requires:

- one coherent camera, lighting model, palette, and edge treatment;
- animation frames that do not visibly jump around their anchor;
- explicit separation of visual bounds from gameplay collision;
- stable asset IDs consumed through a manifest;
- lossless masters with optimized runtime exports;
- a vertical slice approved in motion before full production.

## 2. Current inventory and migration risk

| Family | Current contents | Current characteristics | Migration concern |
|---|---:|---|---|
| Player | idle 20, move 20, shoot 3 | PNG RGBA; roughly 313x206; scaled to 50%; faces right then rotates | Keep aim axis, center, muzzle relationship, and timing stable |
| Zombie | idle 17, move 17, attack 9 | PNG RGBA; canvases vary by state from 241x222 to 318x294; scaled to 50%; rotates | State-dependent bounds can cause visual popping; collision is already intended to remain stable |
| World | one active 5000x5000 JPEG plus three menu/background images | large raster sampled as the camera moves | A replacement must tile or cover the full world without seams and remain cheap to load |
| Projectiles | bullet | 14x14 PNG RGBA | Must remain legible without making its collision footprint larger |
| Throwables | grenade, stun grenade | 19x19 and 10x22 PNG RGBA | Tiny runtime footprint; silhouette and color coding matter more than texture |
| Effects | explosion, stun explosion | 374x297 and 255x220 PNG RGBA, currently static | Should become short animations, but damage/stun radius remains gameplay-owned |
| Power-ups | instant kill, nuke, max ammo, max health | four 150x150 PNG RGBA icons used in-world | Need a shared shape language and readable color coding |
| Wall items | gun pickup | one 150x150 PNG RGBA | Needs an explicit world anchor and interaction marker convention |
| HUD | three panels, two gun icons | mixed canvases from 79x62 to 450x44 | Existing text offsets depend on panel layout; migrate as a complete HUD slice |
| Menu | 135x90 indexed-looking scene scaled with nearest-neighbor; unused/legacy large art also exists | deliberately low-resolution, six-color palette cycling | Choose whether to reinterpret it in HD; do not accidentally smooth-scale the current pixel version |
| Cursor | one 46x45 PNG RGBA | centered visual crosshair | Hotspot must be explicit rather than inferred from dimensions |
| Audio | gun WAV, explosion WAV, legacy gun MP3 | very low playback volume in current code | Inventory and loudness pass should follow visual slice; retain event IDs |

Current file paths contain spaces and mixed capitalization, and frame indices are not zero-padded. Several source sizes are effectively runtime metadata embedded in code. Migration should introduce new files alongside legacy files and remove legacy paths only after all consumers use stable IDs.

## 3. Visual direction

### Tone

- Contemporary survival-horror action, tense rather than bleak.
- Graphic-novel clarity: controlled texture, painted material variation, and crisp silhouettes.
- Ground and props are muted; actors, threats, pickups, and effects carry the strongest local contrast.
- Violence may include stylized impact and debris, but avoid detailed gore in the first production pass.

### Camera and orientation

- Orthographic top-down play view with approximately **15-25 degrees of visible side surface**, consistent across every world asset.
- Characters are authored facing **screen-right (positive X)** at zero rotation. Runtime rotation aims that axis toward the target.
- No baked perspective convergence in actor sprites.
- The ground plane uses a consistent overhead projection. Props must not imply a different horizon or camera height.
- Keep important actor shapes inside a circular safe area so arbitrary runtime rotation does not clip them.

### Lighting and palette

- Key light comes from upper-left in world art, broad and cool-neutral.
- Warm practical/accent light is reserved for weapons, hazards, and objectives.
- Ambient shadows are soft and short. Do not bake long directional actor shadows into animation frames; they rotate incorrectly with the sprite.
- Player accent: desaturated blue/teal. Basic zombie accent: sickly yellow-green. Hostile/damage: warm red-orange. Stun/electrical: cyan-white. Health: green. Ammo: amber.
- Preserve at least three value bands per important object: dark outline/shadow, readable local color, and highlight.
- Avoid pure black over large areas and avoid neon saturation outside gameplay-significant effects.

### Shape and detail hierarchy

At normal gameplay zoom, prioritize in this order:

1. silhouette and facing direction;
2. player-versus-enemy recognition;
3. weapon and attack state;
4. pickup/effect category;
5. surface texture.

Detail that cannot survive a 1080x720 gameplay screenshot is optional. Fine texture must not create shimmer while sprites rotate or move.

## 4. Canvas, anchor, and geometry contract

All positions use normalized canvas coordinates from `(0, 0)` at top-left to `(1, 1)` at bottom-right. Manifest entries carry the authoritative values.

### Actor masters

- Master canvas: **512x512 RGBA**, one actor and weapon per frame.
- Runtime target: **192x192 RGBA** at 1x logical resolution. The loader may produce other resolution tiers from the master/runtime source, but every frame in one animation set must share dimensions.
- Zero-degree facing: right.
- Primary anchor (`pivot`): **(0.50, 0.50)**, the actor's ground-contact/rotation center, held within 2 master pixels across all frames.
- Suggested actor body safe area: x `0.25-0.75`, y `0.25-0.75`. Weapon, hands, and attack motion may extend into the outer area.
- Muzzle socket: normalized coordinate per animation frame when needed. It may move with recoil; it is not the projectile collision origin until gameplay explicitly adopts it.
- Frames must retain at least 24 master pixels of transparent padding on every edge. No nontransparent pixel may touch the canvas edge.
- Do not encode hitboxes in alpha bounds. `collision_size`, attack reach, and separation distance remain explicit gameplay metadata/configuration.

The existing 120x111 zombie collision footprint is the migration baseline and must not change merely because art changes. Record it as legacy-compatible metadata until a separately reviewed balance change replaces it.

### Small world items

| Class | Master canvas | Runtime target | Anchor |
|---|---:|---:|---|
| Bullet/tracer | 128x128 | 24x24 visual canvas | center `(0.50, 0.50)`, authored pointing right |
| Grenade/stun grenade | 256x256 | 48x48 visual canvas | ground center `(0.50, 0.55)` |
| Power-up | 512x512 | 128x128 visual canvas | ground center `(0.50, 0.58)` |
| Wall weapon/item | 512x512 | 160x160 visual canvas | interaction center `(0.50, 0.50)` |
| Crosshair | 256x256 | 48x48 | hotspot `(0.50, 0.50)` |

Runtime visual targets are initial art targets, not permission to resize collision. Review them in the vertical slice at native logical resolution.

### Effects

- Master canvas: **1024x1024 RGBA**; runtime target initially **384x384**.
- Anchor: effect center `(0.50, 0.50)`.
- Keep the perceived center stationary within 3 runtime pixels.
- Alpha may extend broadly, but no frame may clip at the edges.
- Explosion and stun effect radius is visual-only. Damage and stun radius must remain explicit elsewhere.

### UI

- Author HUD at the 1080x720 logical reference size with vector or layered masters.
- Export nine-slice panels when panels need to resize; export standalone icons on square transparent canvases.
- Maintain a 32-pixel safe inset from logical screen edges unless a layout component defines a larger inset.
- Text stays live and rendered by the game; do not bake changing values, labels, scores, or localized copy into panel art.
- Every icon must remain distinguishable at 32x32 and in grayscale. Color is a reinforcement, not the only identifier.

## 5. Transparency and edge quality

- World sprites, actors, items, icons, cursors, and effects export as straight-alpha RGBA PNG or lossless WebP if runtime support is deliberately added.
- Transparent pixels must have clean edge color to avoid dark or light halos when rotated and smooth-scaled.
- No matte background, checkerboard, crop marks, guides, signatures, text fragments, or generative artifacts.
- Do not use semi-transparent pixels inside intended solid silhouettes except for deliberate glass, smoke, glow, or motion effects.
- Review each asset on light gray, dark gray, and representative ground backgrounds.
- JPEG is acceptable only for fully opaque large backgrounds or source references. Never use JPEG for sprites or UI overlays.

## 6. Scaling and filtering

- New illustrated assets use smooth interpolation when scaled. Prefer rendering at their intended logical size; avoid repeated runtime resampling.
- Pixel-art assets use nearest-neighbor only. The current menu backdrop is pixel art and remains nearest-neighbor until replaced as a complete menu-art migration.
- The manifest should declare `filter: smooth | nearest`; callers must not choose ad hoc.
- Use integer dimensions after scaling. Preserve aspect ratio unless an explicitly stretchable UI region uses nine-slice metadata.
- Verify actors at rotations of 0, 45, 90, 135, and 180 degrees. Reject visible edge halos, clipping, or severe shimmer.
- A 2x tier may be added for high-DPI displays only after the 1x vertical slice establishes memory and load budgets.

## 7. Naming and directory convention

Proposed runtime layout:

```text
assets/
  manifest.json
  characters/
    player/rifle/{idle,move,shoot}/
    zombies/basic/{idle,move,attack}/
  effects/{ballistic_hit,explosion,stun}/
  environments/yard/
  items/{powerups,throwables,wall}/
  projectiles/
  ui/{hud,menu,cursor}/
  audio/{weapons,effects,ui}/
```

Rules:

- Lowercase ASCII `snake_case`; no spaces.
- Stable semantic IDs use dotted lowercase names, for example `character.player.rifle.move` and `effect.explosion.grenade`.
- Frame files use zero-padded indices: `frame_00.png`, `frame_01.png`, and so on.
- A state directory contains only the frames for that state plus optional production notes; it does not mix variants.
- Variant names describe gameplay-visible distinctions (`basic`, `armored`, `fast`), not generation attempts (`final2`, `new`, `good`).
- Source working files live outside runtime asset directories, preferably under `art_source/`, mirroring runtime paths.
- Generated provenance should be recorded next to source masters, including tool/model, prompt or brief revision, date, and human edits. Do not ship provenance files in the runtime package.

## 8. Manifest-facing requirements

The implementation owns the exact schema. Art production requires the schema to represent at least:

```json
{
  "character.player.rifle.move": {
    "type": "animation",
    "frames": "characters/player/rifle/move/frame_{frame:02}.png",
    "frame_count": 12,
    "fps": 12,
    "loop": true,
    "canvas": [192, 192],
    "pivot": [0.5, 0.5],
    "filter": "smooth",
    "collision_size": [156, 103],
    "sockets": {"muzzle": "per_frame"}
  }
}
```

The example collision size documents a compatibility value, not a final balance decision. Schema and code tests must establish the authoritative current player footprint before migration.

Minimum fields by type:

- image: `type`, `path`, `canvas` or natural size, `pivot`, `filter`, alpha expectation;
- animation: image fields plus ordered frames/pattern, `frame_count`, `fps`, `loop`;
- UI panel: path, reference size, anchor/layout role, optional nine-slice margins;
- background: path, world coverage or tile dimensions, filtering, opaque flag;
- audio: path, category, loop flag, baseline gain; loudness metadata can follow later.

Asset IDs are public contracts. Renaming a file should not rename its asset ID. Gameplay geometry fields must not silently default from image dimensions.

## 9. Animation requirements

### Initial target sets

| Actor/state | Target frames | Target playback | Loop | Notes |
|---|---:|---:|---|---|
| Player idle | 8-12 | 8-10 fps | yes | restrained breathing; muzzle remains stable |
| Player move | 12 | 12-15 fps | yes | readable gait; no world-position drift within canvas |
| Player shoot | 4-6 | 18-24 fps | no/retrigger | anticipation, recoil, recovery; muzzle socket supplied |
| Basic zombie idle | 8-12 | 8-10 fps | yes | asymmetry without changing apparent footprint |
| Basic zombie move | 12 | 10-12 fps | yes | crowd motion should tolerate randomized phase |
| Basic zombie attack | 8-10 | 12-15 fps | no/retrigger | contact moment called out in production notes |
| Explosion | 10-16 | 20-30 fps | no | flash, body, smoke/debris decay |
| Stun burst | 8-12 | 20-30 fps | no | cyan-white electrical language; distinct from lethal fire |

Rules:

- Animation timing is metadata, not inferred from the global render rate.
- Every frame in a state uses the exact same canvas, pivot, palette, light, costume, weapon proportions, and camera.
- Adjacent frames must preserve identity and topology. No changing fingers, weapon model, clothing, wounds, limb count, or carried equipment.
- Loops must be checked first-to-last as well as frame-to-frame.
- Movement animation is in-place. Root motion remains controlled by simulation.
- Attack and shoot contact frames should be documented even if gameplay does not yet consume animation events.
- Randomized crowd phase is allowed; randomized frame ordering is not.

For image-generation workflows, generate and approve a character reference/turnaround first. Do not prompt each animation frame independently. A rigged, 3D-rendered, or pose-controlled workflow is strongly preferred for final sequences. Generative output is suitable for concept direction, texture exploration, environmental plates, and UI motifs; all final animation frames require continuity cleanup.

## 10. Source and runtime formats

| Asset | Production master | Runtime export |
|---|---|---|
| Characters/items/effects | layered PSD/KRA/ORA or lossless frame sequence at master size | RGBA PNG frames, optimized losslessly |
| HUD/menu components | SVG/Figma/vector or layered raster at 2x reference | SVG only if runtime support exists; otherwise RGBA PNG at approved size |
| World ground | layered large raster or tile source, 16-bit while grading | opaque PNG/WebP preferred; high-quality JPEG only if artifacts are invisible and size benefit is material |
| Audio | 48 kHz, 24-bit WAV master | WAV/OGG according to tested runtime support; avoid MP3 for short latency-sensitive effects |

Keep masters out of the packaged runtime directory. Runtime exports must be reproducible from masters where practical.

## 11. Vertical slice

The first art production milestone proves the contract and style with:

- one full rifle player set: idle, move, shoot;
- one full basic zombie set: idle, move, attack;
- bullet/tracer, grenade, one explosion sequence, and one ballistic impact;
- one representative 1080x720 crop of the active world environment, including quiet and high-detail areas;
- the three primary HUD regions, current weapon icon, health treatment, ammo treatment, cursor, and one power-up;
- no campaign-specific final art until campaign navigation behavior stabilizes.

### Vertical-slice gates

The slice is approved only when:

1. all assets resolve by manifest ID and validate without warnings;
2. no new art path or frame count is hard-coded in an entity;
3. player and zombie collision behavior matches the legacy baseline in automated tests;
4. actors do not clip or wobble through full rotation and animation;
5. player, zombie, pickups, and projectiles are legible during a representative crowded encounter;
6. HUD remains readable at supported window sizes and never overlaps live text;
7. no asset reads occur during active play after preload;
8. startup time and memory are measured against the legacy build;
9. screenshots are reviewed at native 1080x720, not only zoomed in;
10. the art owner approves a captured gameplay clip, since still frames cannot validate animation coherence.

Do not begin bulk production until the slice passes. Changes to camera, canvas, pivot, palette, or filtering after bulk work starts are high-cost migrations.

## 12. Phased migration

1. **Foundation:** implement schema, ID-based loader, validation, filtering, pivots, sockets, and legacy compatibility.
2. **Reference package:** approve palette sheet, material samples, player reference, zombie reference, and environment crop.
3. **Gameplay vertical slice:** produce and integrate the slice above without changing gameplay geometry.
4. **Slice review:** profile, capture gameplay, fix continuity and readability, then freeze art contract version 1.
5. **Family production:** migrate player/weapons, zombies, effects/items, world, then HUD/menu in coherent batches.
6. **Audio pass:** normalize event assets and replace legacy MP3 where appropriate.
7. **Cleanup:** remove legacy references and files only after repository search, manifest validation, and full tests prove they are unused.

Each family migration should be independently reviewable and leave the game playable. Avoid a repository-wide rename before the compatibility layer exists.

## 13. Production handoff checklist

Every artist or image-generation agent receives:

- this specification and the frozen manifest schema version;
- approved palette and lighting reference;
- approved character/environment reference sheet;
- required asset IDs, master/runtime dimensions, frame count, FPS, pivot, sockets, and safe area;
- current gameplay screenshot showing normal on-screen scale;
- explicit exclusions: no text, watermark, matte, baked long shadow, perspective mismatch, edge clipping, or gameplay geometry changes.

Every delivery includes:

- source master or reproducible generation package;
- correctly named runtime exports;
- contact sheet and loop preview for animations;
- light/dark/ground-background edge check;
- manifest metadata proposal;
- provenance and rights/license record;
- note of any intentional departure from this specification.

## 14. Decisions to freeze after the slice

The vertical slice must resolve these before bulk production:

- final player and zombie runtime visual sizes;
- whether menu art becomes HD illustrated art or remains a deliberately separate pixel-art treatment;
- whether world art is one large sheet, chunked sheets, or tiles;
- final animation frame counts and playback rates;
- high-DPI tier and memory budget;
- acceptable gore level;
- runtime compression formats supported by the shipping platforms.

Until those decisions are frozen, production agents should make reference assets and tests, not entire asset families.
