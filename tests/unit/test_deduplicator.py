from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DeduplicationStatus, Lead
from app.services.lead_service import LeadPersistenceService


def lead_candidate(
    source_url: str,
    *,
    name: str = "Example Bike Studio",
    city: str | None = None,
    country: str | None = None,
    platform: str | None = None,
    platform_account_id: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> Lead:
    return Lead(
        name=name,
        source="web",
        source_url=source_url,
        city=city,
        country=country,
        platform=platform,
        platform_account_id=platform_account_id,
        email=email,
        phone=phone,
    )


def persist(session: Session, lead: Lead) -> Lead:
    result = LeadPersistenceService().assess_and_persist(session, lead)
    assert result.created is True
    session.commit()
    return result.lead


def lead_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Lead)) or 0


def test_canonical_url_match_is_confirmed_duplicate_and_is_idempotent(db_session: Session) -> None:
    existing = persist(db_session, lead_candidate("https://example.test"))
    duplicate = lead_candidate("HTTP://EXAMPLE.TEST/")

    result = LeadPersistenceService().assess_and_persist(db_session, duplicate)

    assert result.created is False
    assert result.lead.id == existing.id
    assert result.decision.status is DeduplicationStatus.DUPLICATE
    assert result.decision.match_key == "canonical_url"
    assert lead_count(db_session) == 1


def test_canonical_url_takes_priority_over_lower_ranked_email_match(db_session: Session) -> None:
    canonical_match = persist(
        db_session,
        lead_candidate("https://example.test/canonical", email="first@example.test"),
    )
    persist(db_session, lead_candidate("https://example.test/email", email="shared@example.test"))

    result = LeadPersistenceService().assess_and_persist(
        db_session,
        lead_candidate("http://example.test/canonical/", email="shared@example.test"),
    )

    assert result.created is False
    assert result.lead.id == canonical_match.id
    assert result.decision.match_key == "canonical_url"


def test_platform_account_and_phone_are_confirmed_duplicate_keys(db_session: Session) -> None:
    platform_match = persist(
        db_session,
        lead_candidate(
            "https://example.test/platform",
            platform="Instagram",
            platform_account_id="ExampleBike",
        ),
    )
    platform_result = LeadPersistenceService().assess_and_persist(
        db_session,
        lead_candidate(
            "https://example.test/new-platform",
            platform="instagram",
            platform_account_id="examplebike",
        ),
    )

    assert platform_result.lead.id == platform_match.id
    assert platform_result.decision.match_key == "platform + platform_account_id"

    phone_match = persist(
        db_session,
        lead_candidate("https://example.test/phone", phone="6123 4567", country="SG"),
    )
    phone_result = LeadPersistenceService().assess_and_persist(
        db_session,
        lead_candidate("https://example.test/new-phone", phone="+65 6123 4567", country="SG"),
    )

    assert phone_result.lead.id == phone_match.id
    assert phone_result.decision.match_key == "normalized_phone"


def test_name_and_city_match_requires_human_review(db_session: Session) -> None:
    existing = persist(
        db_session,
        lead_candidate(
            "https://example.test/original",
            name="Example Bike & Co.",
            city="Singapore",
        ),
    )
    result = LeadPersistenceService().assess_and_persist(
        db_session,
        lead_candidate(
            "https://example.test/similar",
            name="example bike co",
            city=" SINGAPORE ",
        ),
    )
    db_session.commit()

    assert result.created is True
    assert result.lead.id != existing.id
    assert result.decision.status is DeduplicationStatus.POSSIBLE_DUPLICATE
    assert result.decision.match_key == "normalized_name + normalized_city"
    assert lead_count(db_session) == 2


def test_no_comparison_key_match_creates_a_new_lead(db_session: Session) -> None:
    persist(db_session, lead_candidate("https://example.test/one", email="one@example.test"))

    result = LeadPersistenceService().assess_and_persist(
        db_session,
        lead_candidate("https://example.test/two", email="two@example.test"),
    )

    assert result.created is True
    assert result.decision.status is DeduplicationStatus.NEW
