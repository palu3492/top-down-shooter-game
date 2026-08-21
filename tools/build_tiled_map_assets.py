#!/usr/bin/env python3
"""Write Tiled metadata for a 10x10 grid of pre-cut 1000px map chunks."""

from pathlib import Path
import csv
import json


ROOT = Path(__file__).resolve().parents[1] / "assets" / "map_10000"
TILES = ROOT / "tiles"


def main() -> None:
    rows = []
    for row in range(10):
        for col in range(10):
            rows.append({
                "row": row,
                "column": col,
                "x_px": col * 1000,
                "y_px": row * 1000,
                "filename": f"tiles/map_r{row:02d}_c{col:02d}.png",
            })

    with (ROOT / "tile_manifest.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    layout = {
        "assembled_size_px": [10000, 10000],
        "grid": {"columns": 10, "rows": 10},
        "chunk_size_px": [1000, 1000],
        "origin": "top-left",
        "ordering": "row-major",
        "tiles": rows,
    }
    (ROOT / "layout.json").write_text(json.dumps(layout, indent=2) + "\n")


if __name__ == "__main__":
    main()
