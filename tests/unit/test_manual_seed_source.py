import json
from pathlib import Path

from app.sources import ManualSeedSource


def write_seed_file(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_manual_seed_source_returns_valid_candidates_and_record_errors(tmp_path: Path) -> None:
    path = write_seed_file(
        tmp_path / "seeds.json",
        {
            "candidates": [
                {
                    "url": "https://example.test/studio",
                    "title": "Example Bike Studio",
                    "snippet": "Custom bike builds",
                },
                {"title": "Missing URL"},
            ]
        },
    )

    result = ManualSeedSource(path).discover()

    assert len(result.candidates) == 1
    assert result.candidates[0].source == "manual_seed"
    assert result.candidates[0].captured_at.tzinfo is not None
    assert result.errors[0].record_index == 1


def test_manual_seed_source_rejects_a_file_without_candidate_collection(tmp_path: Path) -> None:
    path = write_seed_file(tmp_path / "invalid.json", {"records": []})

    try:
        ManualSeedSource(path).discover()
    except ValueError as error:
        assert "candidates array" in str(error)
    else:
        raise AssertionError("Expected an invalid manual-seed file to fail")
