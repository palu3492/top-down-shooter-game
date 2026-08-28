#!/usr/bin/env python3
"""Split the world artwork into chunks and install them as Tiled image layers.

The source artwork is retained. Re-running this command replaces only the
generated chunks and the TMX background image layers; object/collision layers
are left byte-for-byte unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / (
    "Assets/map_10000_cartoon/map_audit_upper_right_bridge_removed_v44b.png"
)
DEFAULT_TMX = PROJECT_ROOT / "Assets/Maps/world_1/world_1.tmx"
DEFAULT_OUTPUT = PROJECT_ROOT / "Assets/Maps/world_1/background_chunks"
CHUNK_SIZE = 1000
GRID_SIZE = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--tmx", type=Path, default=DEFAULT_TMX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def image_size(source: Path) -> tuple[int, int]:
    magick = shutil.which("magick")
    if magick is None:
        raise SystemExit("ImageMagick's 'magick' executable is required")
    result = subprocess.run(
        [magick, "identify", "-format", "%w %h", str(source)],
        check=True,
        capture_output=True,
        text=True,
    )
    width, height = map(int, result.stdout.split())
    return width, height


def split_image(source: Path, output: Path) -> list[dict[str, int | str]]:
    expected = CHUNK_SIZE * GRID_SIZE
    if image_size(source) != (expected, expected):
        raise SystemExit(f"Expected a {expected}x{expected} source image: {source}")

    output.mkdir(parents=True, exist_ok=True)
    for old_chunk in output.glob("map_r??_c??.png"):
        old_chunk.unlink()

    with tempfile.TemporaryDirectory(dir=output) as temporary:
        pattern = Path(temporary) / "chunk_%03d.png"
        subprocess.run(
            ["magick", str(source), "-crop", "1000x1000", "+repage", str(pattern)],
            check=True,
        )
        generated = sorted(Path(temporary).glob("chunk_*.png"))
        if len(generated) != GRID_SIZE * GRID_SIZE:
            raise SystemExit(f"ImageMagick produced {len(generated)} chunks, expected 100")

        rows: list[dict[str, int | str]] = []
        for index, temporary_chunk in enumerate(generated):
            row, column = divmod(index, GRID_SIZE)
            filename = f"map_r{row + 1:02d}_c{column + 1:02d}.png"
            temporary_chunk.replace(output / filename)
            rows.append(
                {
                    "row": row + 1,
                    "column": column + 1,
                    "x_px": column * CHUNK_SIZE,
                    "y_px": row * CHUNK_SIZE,
                    "filename": filename,
                }
            )
    return rows


def write_metadata(source: Path, output: Path, rows: list[dict[str, int | str]]) -> None:
    with (output / "manifest.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    layout = {
        "source": str(source.relative_to(PROJECT_ROOT)),
        "assembled_size_px": [CHUNK_SIZE * GRID_SIZE] * 2,
        "grid": {"columns": GRID_SIZE, "rows": GRID_SIZE},
        "chunk_size_px": [CHUNK_SIZE, CHUNK_SIZE],
        "origin": "top-left",
        "ordering": "row-major",
        "tiles": rows,
    }
    (output / "layout.json").write_text(json.dumps(layout, indent=2) + "\n")


def install_tmx_layers(tmx: Path, output: Path, rows: list[dict[str, int | str]]) -> None:
    document = tmx.read_text()
    matches = list(
        re.finditer(
            r' <imagelayer id="\d+" name="Background(?: r\d{2} c\d{2})?"[^>]*>.*?</imagelayer>\n',
            document,
            flags=re.DOTALL,
        )
    )
    if len(matches) not in (1, GRID_SIZE * GRID_SIZE):
        raise SystemExit(
            f"Expected one old background or 100 generated backgrounds; found {len(matches)}"
        )

    used_ids = {
        int(value)
        for value in re.findall(r'<(?:layer|objectgroup|imagelayer|group) id="(\d+)"', document)
    }
    first_id_match = re.search(r'id="(\d+)"', matches[0].group())
    assert first_id_match is not None
    first_id = int(first_id_match.group(1))
    reusable_ids = {
        int(value)
        for match in matches
        for value in re.findall(r'id="(\d+)"', match.group())
    }
    available_ids = [first_id]
    candidate = 1
    while len(available_ids) < len(rows):
        if candidate not in used_ids or candidate in reusable_ids:
            if candidate not in available_ids:
                available_ids.append(candidate)
        candidate += 1

    relative_output = Path(os.path.relpath(output, tmx.parent))
    layers = []
    for layer_id, row in zip(available_ids, rows):
        chunk_source = (relative_output / str(row["filename"])).as_posix()
        layers.append(
            f' <imagelayer id="{layer_id}" name="Background r{row["row"]:02d} c{row["column"]:02d}" '
            f'offsetx="{row["x_px"]}" offsety="{row["y_px"]}">\n'
            f'  <image source="{chunk_source}" width="{CHUNK_SIZE}" height="{CHUNK_SIZE}"/>\n'
            " </imagelayer>\n"
        )

    start, end = matches[0].start(), matches[-1].end()
    updated = document[:start] + "".join(layers) + document[end:]
    layer_ids = re.findall(
        r'<(?:layer|objectgroup|imagelayer|group) id="(\d+)"', updated
    )
    next_layer_id = max(map(int, layer_ids)) + 1
    updated = re.sub(
        r'nextlayerid="\d+"', f'nextlayerid="{next_layer_id}"', updated, count=1
    )

    temporary = tmx.with_suffix(".tmx.tmp")
    temporary.write_text(updated)
    temporary.replace(tmx)


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    tmx = args.tmx.resolve()
    output = args.output.resolve()
    if not source.is_file() or not tmx.is_file():
        raise SystemExit("Both --source and --tmx must be existing files")

    rows = split_image(source, output)
    write_metadata(source, output, rows)
    install_tmx_layers(tmx, output, rows)
    print(f"Wrote {len(rows)} chunks to {output}")
    print(f"Updated background image layers in {tmx}")


if __name__ == "__main__":
    main()
