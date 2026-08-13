# 2.5D Depth Demo

This fixed-screen prototype tests whether pre-rendered, dimensional artwork can
produce convincing depth in the existing 2D Pygame renderer. It is deliberately
isolated from the main game: there is no scrolling camera, campaign progression,
or replacement of the production art.

## Run

From the repository root, after installing the project dependencies:

```bash
uv run python main.py --demo-2p5d
```

Running `uv run python main.py` without the option still launches the regular
game.

## Controls

| Input | Action |
|---|---|
| `W` `A` `S` `D` or arrow keys | Move within the fixed arena |
| Mouse | Aim |
| Left click | Shoot |
| `R` | Reload; restart after victory or defeat |
| `Space` | Start the encounter |
| `F3` | Toggle collision and anchor debug overlay |
| `Esc` | Leave the demo |

## What to look for

- The player's ground point passes in front of and behind obstacle artwork.
- Collision follows the small footprint at an obstacle's base, not its full
  visible silhouette.
- Zombies approach from the screen edges while retaining readable overlap.
- Player and zombie art selects from eight directions without rotating a flat
  image.
- The three-minute encounter escalates, pauses briefly at midpoint, and ends in
  a clear victory or defeat screen.
- Health and ammunition pickups encourage movement through the obstacle lanes.

The included visuals are temporary proof-of-concept assets. Their purpose is to
validate layering, collision, movement, facing, and crowd readability before
the final asset-production pass.
