# Demo 2.5D modular environment

These are replaceable proof-of-concept assets for the fixed-screen demo. Three
atlases were generated with the built-in image-generation tool, using the user
reference screenshot for style, camera, lighting, and fidelity only. Sources
are preserved under `sources/`; cropped alpha assets are under `props/` and
`decals/`.

All prompts requested polished, painterly pre-rendered 3D game art at a roughly
65-degree overhead camera with warm upper-left lighting on a flat `#ff00ff`
chroma background. The three subjects were: (1) trees, bushes, grasses, and dead
shrubs; (2) fences, barricade, vehicles, barrels, crates, and hay; and (3) wagon,
wheel, rocks, log, stump, boards, puddle, tracks, grass/dirt patches, and pebbles.

ImageMagick chroma removal produced RGBA PNGs. Runtime dimensions, ground
anchors, collision footprints, and tall-prop fade behavior live in
`shooter/demos/environment_map.py`; composition lives in
`shooter/demos/depth_demo_layout.json`. Missing art uses procedural fallbacks.
