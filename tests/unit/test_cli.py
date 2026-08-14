from pytest import raises

from app import __version__
from app.cli import main


def test_cli_returns_success_without_arguments() -> None:
    assert main([]) == 0


def test_cli_prints_version(capsys) -> None:
    with raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"cyclelead {__version__}"
