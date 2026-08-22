"""Filesystem locations shared by headless data and presentation loaders."""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "Assets"


def asset_path(relative):
    return str(ASSETS_DIR / relative)
