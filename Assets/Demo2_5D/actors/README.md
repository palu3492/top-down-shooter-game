# Demo 2.5D directional actors

These are presentation-prototype assets, not final production animation.

## Layout and naming

- Canvas: 256 x 256 RGBA PNG.
- Directions: `n`, `ne`, `e`, `se`, `s`, `sw`, `w`, `nw`.
- Player states: `idle` (4 frames), `move` (6), `fire` (3).
- Zombie states: `run` (6 frames), `attack` (4), `hit` (2), `death` (6).
- Runtime path: `<actor>/<state>/<direction>/frame_XX.png`.
- Ground anchor: bottom-center of the canvas. Visible feet are normalized to the same baseline.

The two source sheets in `sources/` were generated with the built-in image generation tool. The supplied rural-survival gameplay reference defined the elevated camera, warm upper-left light, painterly 3D finish, and gameplay readability. The existing `player.png` and `zombie.png` cutouts defined identity, clothing, equipment, and palette. Each prompt requested exactly eight poses in a 4x2 sheet, ordered N, NE, E, SE, S, SW, W, NW on flat `#ff00ff` chroma.

The chroma sheets were converted to alpha locally, cropped into directions, resized, and bottom-centered. The original chroma and alpha sheets are retained for later replacement or re-export.

## Prototype limitations

- North, northeast, east, southeast, and south use authored sheet poses. Southwest, west, and northwest are clean mirrored counterparts for this placeholder set. Animation frames are deterministic variations of each source pose (small vertical movement, scale/recoil, tint, rotation, and alpha changes), not fully redrawn motion.
- Some extreme rifle/reaching silhouettes were conservatively cropped to prevent neighboring cells from leaking into a direction.
- Death frames simulate collapse/fade rather than showing a true grounded body.
- All eight directions should eventually be rendered from one rigged model or a tightly controlled animation source for production-quality gait, recoil, attacks, and death.

These limitations are intentional: this set proves directional selection, camera consistency, anchors, depth sorting, and the replacement contract before investing in final animation.
