import json
from pathlib import Path

import pygame

from tools.audit_assets import audit_assets, format_report, main


def _save_image(path: Path, size: tuple[int, int], alpha: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = pygame.SRCALPHA if alpha else 0
    pygame.image.save(pygame.Surface(size, flags), path)


def test_audit_detects_sequence_gaps_canvas_and_alpha(tmp_path):
    assets = tmp_path / "Assets"
    _save_image(assets / "hero" / "run_0.png", (32, 32))
    _save_image(assets / "hero" / "run_2.png", (48, 32), alpha=False)

    report = audit_assets(assets)

    assert report["summary"]["images"] == 2
    assert report["sequences"][0]["missing_frames"] == [1]
    codes = {issue["code"] for issue in report["issues"]}
    assert {"missing_frames", "inconsistent_canvas", "inconsistent_alpha"} <= codes
    assert "Issues: 3" in format_report(report)


def test_manifest_discovery_is_schema_agnostic(tmp_path):
    assets = tmp_path / "Assets"
    _save_image(assets / "icons" / "ok.png", (8, 8))
    manifest = tmp_path / "catalog.json"
    manifest.write_text(
        json.dumps(
            {"anything": [{"source": "Assets/icons/ok.png"}, "missing.wav"], "fps": 12}
        )
    )

    report = audit_assets(assets, manifest)

    references = report["manifest"]["references"]
    assert {item["value"] for item in references} == {
        "Assets/icons/ok.png",
        "missing.wav",
    }
    assert report["manifest"]["missing"] == ["missing.wav"]
    assert any(issue["code"] == "missing_manifest_asset" for issue in report["issues"])


def test_cli_can_emit_json(tmp_path, capsys):
    assets = tmp_path / "Assets"
    _save_image(assets / "single.png", (4, 5))

    assert main([str(assets), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["files"][0]["width"] == 4
    assert output["files"][0]["height"] == 5
