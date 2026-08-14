import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DiscoveryRun, DiscoveryRunStatus, Lead, Query, RawCandidate
from app.schemas import SeedInput
from app.services.discovery import DiscoveryService
from app.sources import ManualSeedSource


def write_seed_file(path: Path, candidates: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"candidates": candidates}), encoding="utf-8")
    return path


def test_manual_discovery_persists_candidates_and_is_idempotent(
    db_session: Session,
    tmp_path: Path,
) -> None:
    seed_file = write_seed_file(
        tmp_path / "manual-seeds.json",
        [
            {
                "url": "https://example.test/studio",
                "title": "Example Bike Studio",
                "snippet": "Custom bike builds",
                "country": "SG",
                "city": "Singapore",
            },
            {
                "url": "http://example.test/studio/",
                "title": "Example Bike Studio",
                "snippet": "Custom bike builds",
                "country": "SG",
                "city": "Singapore",
            },
        ],
    )
    service = DiscoveryService()
    seed = SeedInput(query="bike custom build", source="manual_seed", region="Singapore")

    first_run = service.run(db_session, seed, ManualSeedSource(seed_file))
    db_session.commit()
    second_run = service.run(db_session, seed, ManualSeedSource(seed_file))
    db_session.commit()

    assert first_run.status is DiscoveryRunStatus.SUCCESS
    assert first_run.discovered == 2
    assert first_run.parsed == 2
    assert first_run.duplicates == 1
    assert second_run.duplicates == 2
    assert db_session.scalar(select(func.count()).select_from(Lead)) == 1
    assert db_session.scalar(select(func.count()).select_from(RawCandidate)) == 4
    assert db_session.scalar(select(func.count()).select_from(DiscoveryRun)) == 2
    assert db_session.scalar(select(func.count()).select_from(Query)) == 1


def test_manual_discovery_continues_after_invalid_record(
    db_session: Session, tmp_path: Path
) -> None:
    seed_file = write_seed_file(
        tmp_path / "mixed-seeds.json",
        [
            {"url": "https://example.test/valid", "title": "Valid Studio"},
            {"title": "Missing URL"},
        ],
    )

    summary = DiscoveryService().run(
        db_session,
        SeedInput(query="bike repair", source="manual_seed"),
        ManualSeedSource(seed_file),
    )
    db_session.commit()

    assert summary.status is DiscoveryRunStatus.PARTIAL_FAILURE
    assert summary.discovered == 1
    assert summary.parsed == 1
    assert summary.errors == 1


def test_manual_discovery_records_unreadable_file_as_failed_run(
    db_session: Session,
    tmp_path: Path,
) -> None:
    missing_file = tmp_path / "missing.json"

    summary = DiscoveryService().run(
        db_session,
        SeedInput(query="bike workshop", source="manual_seed"),
        ManualSeedSource(missing_file),
    )
    db_session.commit()

    assert summary.status is DiscoveryRunStatus.FAILED
    assert summary.errors == 1
