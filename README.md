# Top-Down Shooter

A top-down zombie wave shooter built with pygame. Survive escalating waves,
spend the cash the horde drops, and don't let them surround you.

![Gameplay](docs/screenshot.jpg)

## Requirements

- Python 3.14 or newer, pinned in `.python-version`. `uv` fetches it for you.
- `pygame-ce` — **not** upstream `pygame`. Don't install both; they claim the
  same `pygame` import name and shadow each other.

## Install (macOS)

[uv](https://github.com/astral-sh/uv) manages the interpreter and the virtual
environment together, so every contributor gets the same Python.

```bash
brew install uv
git clone https://github.com/palu3492/top-down-shooter-game.git
cd top-down-shooter-game
uv sync
```

`uv sync` does everything: fetches the CPython build named in `.python-version`,
creates `.venv`, and installs the exact versions recorded in `uv.lock`. It does
not touch your system or Homebrew Python.

Two things to avoid on macOS:

- **Don't point the project at Homebrew's `python@3.x`.** It's a rolling
  formula; a `brew upgrade` can bump or relink it and break existing virtual
  environments. Use Homebrew to install `uv`, and nothing else Python-related.
- **Never use `/usr/bin/python3`.** That interpreter belongs to the OS.

## Install (other platforms)

`uv` works the same everywhere — `uv sync` is the supported path on Linux and
Windows too.

Without `uv`, pip can install from `pyproject.toml` on Python 3.14+:

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

That resolves the dependency range rather than the exact versions in `uv.lock`,
so it is reproducible only up to `pygame-ce>=2.5.5,<3`.

## Run

```bash
.venv/bin/python main.py
```

`uv run python main.py` also works, and resolves from the same `uv.lock`.

> **Run from the repository root.** Assets are currently loaded through paths
> relative to the working directory, so launching from anywhere else fails with
> a `FileNotFoundError`.

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
| `Esc` | Pause / resume |
| `Q` | Quit — only while paused |
| `\` | Toggle fullscreen |

The window is resizable: the view keeps its 1080×720 proportions and letterboxes
to fit whatever size you drag it to.

Each wave spawns `5 + wave²` zombies. Kills pay $50. Health regenerates slowly
while you stay untouched.

## Development

Before creating or revising visual assets, read [ART_DIRECTION.md](ART_DIRECTION.md).
It identifies the current reference assets and the style rules for world art,
characters, animation, effects, and HUD work.

```bash
uv sync              # includes the dev group: pytest + ruff
uv run pytest        # run the suite
uv run ruff check .  # lint
```

An editable install also provides a `shooter` console script, subject to the
same run-from-the-repo-root caveat above.

Lint, formatting, type-checking, CI, and the test suite are not wired up yet.

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
