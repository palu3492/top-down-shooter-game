#!/usr/bin/env python3
"""Read-only inventory and consistency checks for game assets."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


IMAGE_SUFFIXES = {
    ".bmp",
    ".gif",
    ".jpg",
    ".jpeg",
    ".lbm",
    ".pcx",
    ".png",
    ".pnm",
    ".tga",
    ".tif",
    ".tiff",
    ".webp",
    ".xpm",
}
AUDIO_SUFFIXES = {".mp3", ".ogg", ".wav"}
ASSET_SUFFIXES = IMAGE_SUFFIXES | AUDIO_SUFFIXES
FRAME_RE = re.compile(r"^(.*?)(\d+)([^\d]*)$")


def _issue(
    code: str, message: str, paths: list[str], severity: str = "warning"
) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "paths": paths}


def _image_details(path: Path) -> dict[str, Any]:
    image = pygame.image.load(path)
    masks = image.get_masks()
    has_alpha = bool(image.get_flags() & pygame.SRCALPHA) or masks[3] != 0
    return {
        "width": image.get_width(),
        "height": image.get_height(),
        "mode": "RGBA" if has_alpha else "RGB",
        "has_alpha": has_alpha,
    }


def _walk_manifest_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            item for child in value.values() for item in _walk_manifest_strings(child)
        ]
    if isinstance(value, list):
        return [item for child in value for item in _walk_manifest_strings(child)]
    return []


def _resolve_manifest_path(raw: str, assets_root: Path, manifest: Path) -> Path | None:
    candidate = Path(raw)
    if candidate.suffix.lower() not in ASSET_SUFFIXES:
        return None
    if candidate.is_absolute():
        return candidate
    options = [manifest.parent / candidate, assets_root / candidate]
    if candidate.parts and candidate.parts[0].lower() == assets_root.name.lower():
        options.append(assets_root.parent / candidate)
    return next((path for path in options if path.exists()), options[0])


def audit_assets(assets_root: Path, manifest: Path | None = None) -> dict[str, Any]:
    """Inventory *assets_root* without changing it and return a JSON-safe report."""
    assets_root = assets_root.resolve()
    files: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    sequences: dict[tuple[str, str, str, str], list[tuple[int, dict[str, Any]]]] = (
        defaultdict(list)
    )

    for path in sorted(item for item in assets_root.rglob("*") if item.is_file()):
        relative = path.relative_to(assets_root).as_posix()
        record: dict[str, Any] = {
            "path": relative,
            "type": "image"
            if path.suffix.lower() in IMAGE_SUFFIXES
            else "audio"
            if path.suffix.lower() in AUDIO_SUFFIXES
            else "other",
            "bytes": path.stat().st_size,
        }
        if record["type"] == "image":
            try:
                record.update(_image_details(path))
            except (pygame.error, OSError) as exc:
                record["error"] = str(exc)
                issues.append(
                    _issue(
                        "unreadable_image",
                        f"Could not read image: {relative}",
                        [relative],
                        "error",
                    )
                )
            match = FRAME_RE.match(path.stem)
            if match and "width" in record:
                key = (
                    path.parent.relative_to(assets_root).as_posix(),
                    match[1],
                    match[3],
                    path.suffix.lower(),
                )
                sequences[key].append((int(match[2]), record))
        files.append(record)

    sequence_reports: list[dict[str, Any]] = []
    for (directory, prefix, suffix, extension), frames in sorted(sequences.items()):
        if len(frames) < 2:
            continue
        frames.sort(key=lambda pair: pair[0])
        numbers = [number for number, _ in frames]
        paths = [record["path"] for _, record in frames]
        dimensions = sorted(
            {(record["width"], record["height"]) for _, record in frames}
        )
        missing = sorted(set(range(numbers[0], numbers[-1] + 1)) - set(numbers))
        sequence = {
            "directory": directory,
            "pattern": f"{prefix}<frame>{suffix}{extension}",
            "frames": numbers,
            "missing_frames": missing,
            "dimensions": [list(size) for size in dimensions],
        }
        sequence_reports.append(sequence)
        if missing:
            issues.append(
                _issue(
                    "missing_frames",
                    f"Animation {sequence['pattern']} is missing frames {missing}",
                    paths,
                )
            )
        if len(dimensions) > 1:
            issues.append(
                _issue(
                    "inconsistent_canvas",
                    f"Animation {sequence['pattern']} uses multiple canvas sizes",
                    paths,
                )
            )
        alpha_values = {record["has_alpha"] for _, record in frames}
        if len(alpha_values) > 1:
            opaque = [record["path"] for _, record in frames if not record["has_alpha"]]
            issues.append(
                _issue(
                    "inconsistent_alpha",
                    f"Some frames in {sequence['pattern']} lack an alpha channel",
                    opaque,
                )
            )

    manifest_report: dict[str, Any] | None = None
    if manifest is not None:
        manifest = manifest.resolve()
        manifest_report = {"path": str(manifest), "references": [], "missing": []}
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(
                _issue(
                    "invalid_manifest",
                    f"Could not read manifest {manifest}: {exc}",
                    [str(manifest)],
                    "error",
                )
            )
        else:
            for raw in sorted(set(_walk_manifest_strings(data))):
                resolved = _resolve_manifest_path(raw, assets_root, manifest)
                if resolved is None:
                    continue
                exists = resolved.is_file()
                reference = {"value": raw, "resolved": str(resolved), "exists": exists}
                manifest_report["references"].append(reference)
                if not exists:
                    manifest_report["missing"].append(raw)
                    issues.append(
                        _issue(
                            "missing_manifest_asset",
                            f"Manifest asset does not exist: {raw}",
                            [raw],
                            "error",
                        )
                    )

    return {
        "assets_root": str(assets_root),
        "summary": {
            "files": len(files),
            "images": sum(item["type"] == "image" for item in files),
            "audio": sum(item["type"] == "audio" for item in files),
            "bytes": sum(item["bytes"] for item in files),
            "issues": len(issues),
        },
        "files": files,
        "sequences": sequence_reports,
        "issues": issues,
        "manifest": manifest_report,
    }


def format_report(report: dict[str, Any]) -> str:
    """Render a compact, human-readable version of an audit report."""
    summary = report["summary"]
    lines = [
        f"Asset audit: {report['assets_root']}",
        (
            f"Files: {summary['files']} "
            f"({summary['images']} images, {summary['audio']} audio), "
            f"{summary['bytes']:,} bytes"
        ),
        f"Animation sequences: {len(report['sequences'])}",
        f"Issues: {summary['issues']}",
    ]
    for issue in report["issues"]:
        lines.append(
            f"[{issue['severity'].upper()}] {issue['code']}: {issue['message']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets_root", nargs="?", type=Path, default=Path("Assets"))
    parser.add_argument(
        "--manifest", type=Path, help="Optional JSON manifest to validate"
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Emit machine-readable JSON"
    )
    args = parser.parse_args(argv)
    report = audit_assets(args.assets_root, args.manifest)
    print(json.dumps(report, indent=2) if args.as_json else format_report(report))
    return 1 if any(issue["severity"] == "error" for issue in report["issues"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
