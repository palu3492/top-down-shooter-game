from __future__ import annotations

import main


def test_main_runs_the_game_by_default(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main, "_run_game", lambda: calls.append("game"))
    monkeypatch.setattr(main, "_run_depth_demo", lambda: calls.append("demo"))

    main.main([])

    assert calls == ["game"]


def test_main_can_select_the_depth_demo(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main, "_run_game", lambda: calls.append("game"))
    monkeypatch.setattr(main, "_run_depth_demo", lambda: calls.append("demo"))

    main.main(["--demo-2p5d"])

    assert calls == ["demo"]
