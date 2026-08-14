import json
from pathlib import Path

from pytest import raises

from app import __version__
from app.cli import main
from app.db import Base, create_db_engine


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
