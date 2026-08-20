import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pytest import raises

from app import __version__
from app.cli import main
from app.config import Settings
from app.db import Base, create_db_engine, create_session_factory
from app.models import (
    BusinessType,
    DiscoveryRun,
    DiscoveryRunStatus,
    Lead,
    ReviewStatus,
    ScoreBand,
)


def test_cli_returns_success_without_arguments() -> None:
    assert main([]) == 0


def test_cli_prints_version(capsys) -> None:
    with raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"cyclelead {__version__}"


def test_cli_runs_manual_discovery_against_configured_database(tmp_path: Path, capsys) -> None:
    database_path = tmp_path / "cli.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    seed_file = tmp_path / "seeds.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "url": "https://example.test/cli",
                    "title": "CLI Bike Studio",
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "discover",
            "--query",
            "bike workshop",
            "--source",
            "manual_seed",
            "--input",
            str(seed_file),
            "--database-url",
            database_url,
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["discovered"] == 1


def test_cli_requires_an_input_file_for_manual_seed_discovery(capsys) -> None:
    exit_code = main(["discover", "--query", "bike workshop", "--source", "manual_seed"])

    assert exit_code == 2
    assert "--input is required" in capsys.readouterr().err


def test_cli_requires_local_configuration_before_brave_search(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "app.cli.get_settings",
        lambda: Settings(brave_search_api_key=None, _env_file=None),
    )

    exit_code = main(["discover", "--query", "bike workshop", "--source", "brave_search"])

    assert exit_code == 2
    assert "CYCLELEAD_BRAVE_SEARCH_API_KEY" in capsys.readouterr().err


def test_cli_lists_and_records_manual_reviews(tmp_path: Path, capsys) -> None:
    database_path = tmp_path / "reviews.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    lead = Lead(
        name="CLI Review Studio",
        source="manual_seed",
        source_url="https://example.test/cli-review",
        business_type=BusinessType.BIKE_WORKSHOP,
        score=80,
        score_band=ScoreBand.A,
    )
    session.add(lead)
    session.commit()
    lead_id = lead.id
    session.close()
    engine.dispose()

    queue_exit_code = main(["review-queue", "--database-url", database_url])

    assert queue_exit_code == 0
    assert json.loads(capsys.readouterr().out) == [
        {
            "lead_id": lead_id,
            "name": "CLI Review Studio",
            "business_type": "BIKE_WORKSHOP",
            "score": 80,
            "score_band": "A",
            "score_reasons": [],
            "country": None,
            "city": None,
            "website": None,
            "social_url": None,
            "email": None,
            "phone": None,
            "source_url": "https://example.test/cli-review",
        }
    ]

    review_exit_code = main(
        [
            "review",
            "--lead-id",
            lead_id,
            "--decision",
            "ACCEPT",
            "--reason",
            "Confirmed workshop.",
            "--database-url",
            database_url,
        ]
    )

    review_payload = json.loads(capsys.readouterr().out)
    assert review_exit_code == 0
    assert review_payload["lead_id"] == lead_id
    assert review_payload["decision"] == "ACCEPT"
    assert review_payload["reason"] == "Confirmed workshop."


def test_cli_exports_human_accepted_leads(tmp_path: Path, capsys) -> None:
    database_path = tmp_path / "exports.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    lead = Lead(
        name="CLI Export Studio",
        source="manual_seed",
        source_url="https://example.test/cli-export",
        business_type=BusinessType.BIKE_WORKSHOP,
        score=80,
        score_band=ScoreBand.A,
        score_reasons=["Evidence-backed score reason."],
        review_status=ReviewStatus.ACCEPT,
    )
    session.add(lead)
    session.commit()
    session.close()
    engine.dispose()
    output_path = tmp_path / "accepted.csv"

    exit_code = main(
        [
            "export",
            "--format",
            "csv",
            "--output",
            str(output_path),
            "--database-url",
            database_url,
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    with output_path.open(encoding="utf-8-sig", newline="") as output:
        rows = list(csv.DictReader(output))
    assert exit_code == 0
    assert payload["scope"] == "accepted"
    assert payload["exported"] == 1
    assert rows[0]["lead_id"] == lead.id


def test_cli_reports_a_persisted_discovery_run(tmp_path: Path, capsys) -> None:
    database_path = tmp_path / "reports.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    started_at = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)
    run = DiscoveryRun(
        query="bike workshop",
        source="manual_seed",
        status=DiscoveryRunStatus.SUCCESS,
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=2),
        discovered_count=3,
        parsed_count=3,
        duplicate_count=1,
        qualified_count=1,
        rejected_count=1,
        error_count=0,
    )
    session.add(run)
    session.commit()
    run_id = run.id
    session.close()
    engine.dispose()

    exit_code = main(["report", "--run-id", run_id, "--database-url", database_url])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "run_id": run_id,
        "query": "bike workshop",
        "source": "manual_seed",
        "status": "SUCCESS",
        "started_at": "2026-08-20T09:00:00",
        "finished_at": "2026-08-20T09:00:02",
        "elapsed_seconds": 2.0,
        "discovered": 3,
        "parsed": 3,
        "duplicates": 1,
        "qualified": 1,
        "rejected": 1,
        "errors": 0,
    }
