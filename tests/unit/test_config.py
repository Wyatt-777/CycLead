from pydantic import ValidationError
from pytest import raises

from app.config import Settings


def test_default_settings_match_mvp_contract() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///data/cyclelead.db"
    assert settings.qualification_threshold == 60


def test_qualification_threshold_must_be_a_score() -> None:
    with raises(ValidationError):
        Settings(qualification_threshold=101, _env_file=None)
