# Top-Down Shooter

A top-down zombie wave shooter built with pygame. Survive escalating waves,
spend the cash the horde drops, and don't let them surround you.

![Gameplay](docs/screenshot.jpg)

## Requirements

- Python 3.10 or newer. Development targets **3.14**, pinned in `.python-version`.
- `pygame-ce` — **not** upstream `pygame`. Don't install both; they claim the
  same `pygame` import name and shadow each other.

## Install (macOS)

[uv](https://github.com/astral-sh/uv) manages the interpreter and the virtual
environment together, so every contributor gets the same Python.

```bash
brew install uv
git clone https://github.com/palu3492/top-down-shooter-game.git
cd top-down-shooter-game
uv python install
uv venv
uv pip install -r requirements.txt
```

`uv python install` reads `.python-version` and fetches a standalone CPython
build — it does not touch your system or Homebrew Python.

Two things to avoid on macOS:

- **Don't point the project at Homebrew's `python@3.x`.** It's a rolling
  formula; a `brew upgrade` can bump or relink it and break existing virtual
  environments. Use Homebrew to install `uv`, and nothing else Python-related.
- **Never use `/usr/bin/python3`.** That interpreter belongs to the OS.

## Install (other platforms, or without uv)

`requirements.txt` is a plain pip file, so the standard flow works anywhere:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows: `py -m venv .venv` and `.venv\Scripts\pip install -r requirements.txt`.
Match the version in `.python-version` if you can.

## Run

```bash
.venv/bin/python main.py
```

`uv run python main.py` also works, but note it resolves dependencies from
`pyproject.toml` (`pygame-ce>=2.5.5,<3`) rather than the exact pin in
`requirements.txt`, so the two can drift once a newer pygame-ce ships.

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
| `\` | Toggle fullscreen |
| `P` | Quit |

Each wave spawns `5 + wave²` zombies. Kills pay $50. Health regenerates slowly
while you stay untouched.

## Development

```bash
uv pip install -r requirements-dev.txt   # adds ruff + pytest
uv pip install -e .                      # editable install
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
