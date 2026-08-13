"""Command-line entry point for the game and its development demos."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Top-Down Shooter")
    parser.add_argument(
        "--demo-2p5d",
        action="store_true",
        help="run the fixed-screen 2.5D depth-sorting proof of concept",
    )
    return parser


def _run_game() -> None:
    from shooter.game import game_loop

    game_loop()


def _run_depth_demo() -> None:
    from shooter.demos.depth_demo import run_demo

    run_demo()


def main(argv: Sequence[str] | None = None) -> None:
    """Parse command-line options and start the selected experience."""
    args = _build_parser().parse_args(argv)
    if args.demo_2p5d:
        _run_depth_demo()
    else:
        _run_game()


if __name__ == "__main__":
    main()
