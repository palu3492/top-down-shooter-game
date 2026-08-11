# Top-Down Shooter

A top-down zombie wave shooter built with pygame. Survive escalating waves,
spend the cash the horde drops, and don't let them surround you.

![Gameplay](docs/screenshot.jpg)

## Requirements

- Python 3.10 or newer
- `pygame-ce` (installed by the steps below — **not** upstream `pygame`, see
  [Why pygame-ce](#why-pygame-ce))

## Install

```bash
git clone https://github.com/palu3492/top-down-shooter-game.git
cd top-down-shooter-game
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows the last two lines are `py -m venv .venv` and
`.venv\Scripts\pip install -r requirements.txt`.

## Run

```bash
.venv/bin/python main.py
```

> **Run from the repository root.** Assets are currently loaded through paths
> relative to the working directory, so launching from anywhere else fails with
> a `FileNotFoundError`. AT3 makes asset paths package-relative and removes this
> restriction.

## Controls

| Input | Action |
|---|---|
| `W` `A` `S` `D` | Move |
| Mouse | Aim |
| Left click | Shoot |
| `R` | Reload |
| `G` | Throw frag grenade (5 to start) |
| `F` | Throw stun grenade (5 to start) |
| `Space` | Skip the between-wave timer and start the next wave |
| `\` | Toggle fullscreen |
| `P` | Quit |

Each wave spawns `5 + wave²` zombies. Kills pay $50. Health regenerates slowly
while you stay untouched.

## Why pygame-ce

**pygame is not deprecated.** [`pygame-ce`](https://pyga.me) is a *fork*, not an
official successor — created by pygame's former core developers, in their words,
"after impossible challenges prevented them from continuing development
upstream." Both projects still exist. This is a choice between them, not a
forced upgrade.

The choice is made on maintenance, checked 2026-08-11:

| | upstream `pygame` | `pygame-ce` |
|---|---|---|
| Latest release | 2.6.1, 2024-09-29 | 2.5.8, 2026-08-09 |
| Time since release | ~23 months | ~2 days |
| Highest CPython wheel | 3.13 | 3.14 |
| Installs on CPython 3.14 | no | yes |

`pip install pygame` fails outright on CPython 3.14 — no wheel exists for any
released version, and the fallback source build errors out. Staying upstream
would mean pinning this project to Python 3.13 or older on a package that has
not shipped in nearly two years.

**No source changes were required to adopt it.** pygame-ce installs under the
`pygame` import name and is API-compatible, so every `import pygame` in this
repo works untouched. This was verified by running the original, unmodified
2017-era code against it — see AT1.

One constraint worth keeping: pygame-ce is a *superset* of pygame. Treat the
upstream pygame 2.6 API as the contract and avoid ce-only additions unless the
tradeoff is deliberate. Hold that line and reverting is a one-line change to
`requirements.txt`.

Do not install both — they claim the same `pygame` import name and shadow each
other. If upstream pygame is already in your environment, `pip uninstall pygame`
first.

## Development

```bash
.venv/bin/pip install -r requirements-dev.txt   # adds ruff + pytest
.venv/bin/pip install -e .                      # editable install
```

An editable install also provides a `shooter` console script, subject to the
same run-from-the-repo-root caveat above.

Lint, formatting, type-checking, CI, and the test suite are not wired up yet —
they land in AT10 and AT11.

## Project layout

```
main.py                      entry point
shooter/
  game.py                    main loop, collision helpers
  background.py              scrolling background sheet
  entities/
    player.py                the survivor
    zombie.py                enemy spawning, pathing, health
    projectiles.py           bullets, grenades, explosions
    powerups.py              pickups
  ui/
    hud.py                   HUD, health bar, ammo, cash
    radar.py                 minimap
  systems/
    waves.py                 wave timing and scaling
Assets/                      images and sounds
```

## Modernization backlog

This is an eight-year-old codebase being brought forward in reviewable slices.
See [AARON_TICKETS.md](AARON_TICKETS.md) for the plan — tickets are identified
`AT<N>` and each one is a single PR against `dev`.

There are known bugs still in the backlog, including a crash: a power-up left
on the field for ~7 seconds loads a missing `Human.png` and takes the process
down (AT4).
