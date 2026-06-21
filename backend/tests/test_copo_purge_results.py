"""Tests for CO-PO purge results directory sweep."""

from __future__ import annotations

from pathlib import Path

from app.copo.services.cleanup_service import _sweep_results_directory


def test_sweep_results_directory_removes_copo_result_files(tmp_path, monkeypatch):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    keep = results_dir / "notes.txt"
    keep.write_text("keep")
    target = results_dir / "ADC_ab12cd34ef_CO_PO_Percentage_Results.xlsx"
    target.write_bytes(b"fake")

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("S", (), {"results_dir": str(results_dir)})(),
    )

    removed = _sweep_results_directory()
    assert removed == 1
    assert not target.exists()
    assert keep.exists()
