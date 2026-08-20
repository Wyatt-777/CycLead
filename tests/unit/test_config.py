from pydantic import ValidationError
from pytest import raises

from app.config import Settings


def test_default_settings_match_mvp_contract() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.database_url == "sqlite:///data/cyclelead.db"
    assert settings.qualification_threshold == 60
    assert settings.brave_search_api_key is None
    assert settings.brave_search_country == "US"
    assert settings.brave_search_language == "en"
    assert settings.brave_search_result_count == 10
    assert settings.brave_search_timeout_seconds == 10


def test_qualification_threshold_must_be_a_score() -> None:
    with raises(ValidationError):
        Settings(qualification_threshold=101, _env_file=None)


def test_brave_search_result_count_is_bounded_by_the_api_contract() -> None:
    with raises(ValidationError):
        Settings(brave_search_result_count=21, _env_file=None)
