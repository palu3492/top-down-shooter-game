# Art Direction: Top-Down Shooter

This is the visual source of truth for new and revised game art. Read it before
creating assets, UI, effects, or animations. The repository contains art from
more than one stage of development; follow the reference hierarchy below rather
than averaging every file together.

## Reference hierarchy

Use these assets as the primary style references:

1. `Assets/Props/tree.png`, `tree_damaged.png`, and `tree_critical.png`
2. `Assets/Props/rock.png` and its damaged/critical/ruined states
3. `Assets/Backgrounds/grass_tile.png`
4. `Assets/Player Animations/` and the current frames under
   `Assets/Zombie Animations/`
5. `Assets/HUD/icons/`, `Assets/HUD/throwables/`, and the olive panels drawn in
   `shooter/ui/hud.py`

The old `docs/screenshot.jpg`, `Assets/Backgrounds/background_0.jpg`, legacy HUD
panel images, and bright cyan power-up cards document earlier iterations. They
can clarify function and placement, but their flat shapes, pale ground, and
placeholder-like UI are **not** the quality or style target for new work.

## The visual thesis

The game is a colorful, readable, slightly grim top-down zombie survival game.
It should feel illustrated rather than pixel-art or realistic: bold mobile-game
clarity, hand-painted surface variation, and comic/cel-shaded forms seen from a
high three-quarter top-down camera. The world is lush and inviting; the combat
subjects introduce mud, rot, military equipment, and danger.

Aim for “stylized survival adventure,” not horror realism. Shapes are friendly
and rounded at a distance, while cracks, torn cloth, wounds, weapons, and heavy
shadows supply the menace up close.

## Camera, shape, and readability

- All world objects and characters use a consistent high top-down view. Show
  mostly top surfaces, with enough front/side face to communicate volume.
- Favor compact, chunky silhouettes. Exaggerate the identifying feature: a
  tree's round crown, a rock's split mass, a zombie's reaching hands, a rifle's
  long barrel.
- Use asymmetry inside an overall simple silhouette. Leaf clumps, stones,
  cracks, patches, straps, and tears keep forms handmade without making their
  outer contour noisy.
- Important gameplay objects must read at their in-game size, not only when the
  source PNG is enlarged. Separate major masses before adding texture.
- Preserve transparent padding, orientation, apparent footprint, and pivot
  placement across animation frames and damage-state swaps. Ground contact must
  not jump.

## Rendering language

- Use confident dark outlines and dark contact/occlusion shadows. Outlines are
  near-black tinted toward deep green, brown, or charcoal rather than pure
  mechanical black everywhere.
- Model forms with a small number of broad, clustered value steps. Transitions
  may be softly painted inside a cluster, but the overall read is cel-shaded.
- Light generally comes from the upper-left/top. Keep bright accents on upper
  planes and deep shadow beneath canopies, bodies, equipment, and overlapping
  stones.
- Texture is organic and selective: leaf clusters, grass blades, stone facets,
  cloth folds, scuffs, cracks, and moss. Avoid uniform noise, photographic
  texture, airbrushed plastic, or razor-sharp vector perfection.
- Edges are clean enough to survive scaling, with no colored halo or matte on
  transparent sprites.

## Color and contrast

- The environment is dominated by vivid yellow-green and mid-green foliage,
  warmed by ochre wood and softened gray-brown stone.
- Props use richer light-facing colors and deep green/brown undersides. Small
  yellow flowers, pale stones, and bright leaf tips are appropriate accents.
- The player stays comparatively dark and desaturated: blue-gray clothing,
  charcoal shadows, brown/tan pack and gear, and restrained warm weapon parts.
  This grounded military palette distinguishes the survivor from the grass.
- Zombies use dirty tan clothing, gray pants, brown boots, and sickly
  yellow-green skin. Wounds and holes add muted red-brown accents; do not turn
  the whole enemy into saturated gore.
- Reserve the brightest values and saturation for gameplay signals: health
  red/green, gold currency, pickup glows, explosions, and other immediate
  feedback.
- Maintain value separation from the bright grass. Characters require dark
  contour/underside shapes; small pickups may need a dark rim or localized
  shadow.

## Environment assets

### Grass and terrain

`grass_tile.png` is the ground target: dense, painterly yellow-green turf with
layered blades, scattered broad leaves, tiny flowers, and occasional embedded
pebbles. Its contrast is intentionally low enough to remain a background.

New terrain tiles should be seamless and avoid obvious repeated landmarks.
Keep large-scale value changes gentle. Detail can be plentiful, but it must not
compete with characters, harvestable props, projectiles, or pickups.

### Trees

Trees are compact, almost circular masses built from overlapping scalloped leaf
clusters. The top is lime/yellow-green; lower tiers step through medium green
to very dark teal-green. A warm brown trunk and small flowers/stones anchor the
base. The outline is dark and irregular, not a perfect geometric circle.

Damage must tell a continuous structural story. The healthy tree begins full;
the damaged state loses selected leaf clusters and exposes broken branches; the
critical state reveals the branch skeleton while retaining sparse leaves and
the recognizable planted base. Do not indicate damage only with a tint or a
generic decal.

### Rocks

Rocks are squat rounded boulders with a broad footprint, dark underside, and a
few satellite pebbles. Their volume is described by irregular faceted planes in
warm gray, taupe, and olive-gray, with restrained moss on upper surfaces.

As damage increases, cracks widen and the silhouette breaks into separated
chunks. Keep the same material, lighting, footprint, and approximate mass so
each state clearly depicts the same rock. The ruined state should read as a
collapsed pile, not a newly spawned object.

## Characters and animation

The player and zombies are illustrated at a higher source resolution and scaled
down in game. Retain the thick, slightly rough contour, simplified anatomy, and
broad painted shading of the current frames.

The survivor is a practical, visually dense military silhouette: dark torso,
large tan pack, visible straps/gear, and a weapon projecting clearly from the
body. The pack and shoulders form the central mass; limbs and weapon communicate
pose and aim. Avoid tiny realistic proportions that disappear at gameplay size.

Zombies are broad, shambling human forms viewed largely from above. Oversized
yellow-green hands, torn sleeves, exposed wounds, ripped knees, dirty clothing,
and scuffed boots sell the enemy immediately. Their reaching hands and uneven
limbs should make attacks readable without requiring facial detail.

For animation:

- Keep the torso/core stable enough that the sprite does not vibrate in place.
- Animate from strong contact and passing poses; motion should feel weighty and
  lopsided, not floaty.
- Preserve consistent canvas/pivot rules within a state.
- Let extremities, straps, sleeves, and the weapon provide secondary motion,
  while preserving the silhouette and aim direction.
- Check every sequence at actual game scale and speed, not only frame-by-frame.

## HUD and icons

The current HUD language is rugged military equipment presented with polished
game-icon readability. Panels are layered rounded shapes: near-black/deep olive
outer edge, muted olive rim, dark green inner field, and a thin yellow-olive
highlight. The weapon selector is circular; inventory and ammo modules are
compact rounded boxes.

- UI icons are more polished and saturated than world sprites, but retain the
  same chunky, outlined, cel-rendered language.
- Hearts are glossy saturated red; coins are warm gold; grenade icons are
  olive-drab with clear metal details. Each has a dark contour and a simple
  silhouette that reads at roughly 40–60 pixels.
- Text and numerals are bold white with a heavy dark edge. Information must
  remain legible over bright grass and during combat.
- Use color semantically and sparingly. Olive is the neutral frame; red is
  health/danger; green is healthy/positive; gold is currency/ammunition value.
- New power-up art should become a recognizable illustrated icon inside this
  system. Do not copy the flat cyan octagon-and-label treatment of the legacy
  cards as the final style.
- Avoid generic flat gray rectangles, thin borders, unoutlined type, and UI
  colors unrelated to the olive/gold/red/green vocabulary.

## Effects and pickups

Effects may temporarily exceed the normal saturation and brightness range, but
should still use bold silhouettes and layered painted shapes. Give explosions a
hot core, warm orange/red body, and dark smoke/debris edge. Stun effects should
read as a distinct electrical/flash event rather than a recolored explosion.

Resource pickups should be simplified, clean miniature versions of their source
material. They need stronger isolation and less detail than the harvestable
world prop so they are identifiable instantly.

## Asset-production checklist

Before accepting new art, verify:

- It matches the high top-down perspective and upper-left lighting.
- The silhouette reads on the bright grass at actual game size.
- Outlines, shadow depth, and clustered cel-shading match nearby assets.
- The palette supports the environment/character/UI role described above.
- Transparent edges are clean and the sprite has no accidental background.
- Related frames or states share canvas, pivot, scale, and ground contact.
- Damage is structural and progressive, not merely a hue shift.
- Tiles repeat seamlessly without an obvious grid.
- UI remains readable in motion and uses the olive military frame language.
- The result looks illustrated and game-ready—not photographic, flat-vector,
  low-resolution pixel art, or a placeholder geometric shape.

