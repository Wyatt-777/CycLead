from app.pipeline.normalizer import (
    LeadIdentityInput,
    normalize_business_name,
    normalize_email,
    normalize_identity,
    normalize_phone,
    normalize_url,
)


def test_url_normalization_compares_http_and_https_without_tracking_fragments() -> None:
    raw_url = " HTTP://Example.TEST/?utm_source=search&gclid=abc#contact "

    assert normalize_url(raw_url) == "https://example.test"


def test_url_normalization_preserves_non_tracking_query_parameters() -> None:
    raw_url = "https://example.test/catalog/?ref=summer&source=directory&utm_campaign=launch"

    assert normalize_url(raw_url) == "https://example.test/catalog?ref=summer&source=directory"


def test_contact_normalization_returns_only_verifiable_comparison_values() -> None:
    assert normalize_email(" SALES@Example.TEST ") == "sales@example.test"
    assert normalize_email("not-an-email") is None
    assert normalize_phone("6123 4567", "SG") == "+6561234567"
    assert normalize_phone("6123 4567", None) is None
    assert normalize_phone("not-a-number", "SG") is None


def test_identity_normalization_does_not_guess_missing_values() -> None:
    identity = normalize_identity(
        LeadIdentityInput(
            source_url="not-a-url",
            name=" Example Bike & Co. ",
            city=" Singapore ",
            country=None,
            platform=" Instagram ",
            platform_account_id=" ExampleBike ",
            email=None,
            phone="6123 4567",
        )
    )

    assert identity.canonical_url is None
    assert identity.normalized_email is None
    assert identity.normalized_phone is None
    assert identity.normalized_name == "example bike co"
    assert identity.normalized_city == "singapore"
    assert identity.platform == "instagram"
    assert identity.platform_account_id == "examplebike"
    assert normalize_business_name(" ") is None
