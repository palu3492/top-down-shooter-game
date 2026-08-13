# Demo 2.5D placeholder assets

These generated PNGs are disposable proof-of-concept art. They share a semi-realistic painted 3D look, an approximately 65-degree overhead camera, and warm upper-left lighting. Runtime code should scale them independently from collision geometry.

## Files and geometry

| File | Intended ground anchor | Suggested collision footprint at demo scale |
|---|---:|---:|
| `player.png` | `(0.50, 0.94)` | `34 x 22` ellipse |
| `zombie.png` | `(0.50, 0.94)` | `32 x 20` ellipse |
| `bush.png` | `(0.50, 0.82)` | `88 x 38` ellipse |
| `tree.png` | `(0.50, 0.96)` | `42 x 26` ellipse around trunk |
| `car.png` | `(0.50, 0.82)` | `150 x 64` rotated rectangle |
| `fence.png` | `(0.50, 0.84)` | `132 x 18` rotated rectangle |
| `ground.png` | n/a | none; scale/crop to the fixed viewport |

Anchors are normalized image coordinates. Collision values are starting points in logical screen pixels and should be tuned in motion.

## Prompt summary

- Ground: rural survival arena ground only, broad dirt paths and olive grass, 16:9, no actors, UI, or large obstacles.
- Player: isolated modern survival soldier with rifle, facing right, readable tactical silhouette.
- Atlas: five isolated subjects in fixed cells: running zombie, bush, abandoned pickup, broken fence, and tree.
- Shared style: polished semi-realistic painted 3D game art, 65-degree overhead camera, warm upper-left late-afternoon light.
- Cutouts: generated on flat `#ff00ff`, keyed locally to alpha, trimmed, and padded by 20 pixels.

The original keyed renders and a rejected player attempt are retained in `sources/` for traceability. Replace these placeholders rather than building gameplay behavior around their exact pixel bounds.
