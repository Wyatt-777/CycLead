"""Deterministic normalization for comparison keys without data enrichment."""

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import phonenumbers

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
TRACKING_QUERY_PARAMETERS = {
    "dclid",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "msclkid",
}


@dataclass(frozen=True, slots=True)
class LeadIdentityInput:
    """Raw comparison fields from one parsed or manually entered candidate."""

    source_url: str | None
    name: str | None
    city: str | None
    country: str | None
    platform: str | None
    platform_account_id: str | None
    email: str | None
    phone: str | None


@dataclass(frozen=True, slots=True)
class NormalizedLeadIdentity:
    """Only comparison values that can be derived deterministically from supplied data."""

    canonical_url: str | None
    platform: str | None
    platform_account_id: str | None
    normalized_email: str | None
    normalized_phone: str | None
    normalized_name: str | None
    normalized_city: str | None


def normalize_url(value: str | None) -> str | None:
    """Normalize an HTTP(S) URL for comparison without requesting it or following redirects."""

    if value is None:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    try:
        parsed = urlsplit(candidate)
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None

    if parsed.scheme.lower() not in {"http", "https"} or not host or parsed.username:
        return None

    try:
        normalized_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None

    if ":" in normalized_host and not normalized_host.startswith("["):
        normalized_host = f"[{normalized_host}]"

    input_scheme = parsed.scheme.lower()
    if input_scheme == "http" and port in {None, 80}:
        scheme = "https"
        normalized_port = None
    else:
        scheme = input_scheme
        normalized_port = None if port in {None, 80 if scheme == "http" else 443} else port

    netloc = normalized_host if normalized_port is None else f"{normalized_host}:{normalized_port}"
    path = parsed.path.rstrip("/")
    query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in TRACKING_QUERY_PARAMETERS
            and not key.casefold().startswith("utm_")
        ],
        doseq=True,
    )
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_email(value: str | None) -> str | None:
    """Return a lowercase syntactically valid email or None without provider-specific guesses."""

    if value is None:
        return None

    candidate = unicodedata.normalize("NFKC", value).strip().casefold()
    return candidate if EMAIL_PATTERN.fullmatch(candidate) else None


def normalize_phone(value: str | None, country: str | None) -> str | None:
    """Return an E.164 number only when the supplied number and country are verifiable."""

    if value is None:
        return None

    candidate = unicodedata.normalize("NFKC", value).strip()
    if not candidate:
        return None

    region = None
    if country is not None:
        cleaned_country = country.strip().upper()
        if len(cleaned_country) == 2 and cleaned_country.isalpha():
            region = cleaned_country

    if not candidate.startswith("+") and region is None:
        return None

    try:
        parsed = phonenumbers.parse(candidate, region)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_business_name(value: str | None) -> str | None:
    """Create a punctuation-insensitive business-name comparison key."""

    normalized_text = normalize_text(value)
    if normalized_text is None:
        return None

    punctuation_as_space = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in normalized_text
    )
    return " ".join(punctuation_as_space.split()) or None


def normalize_text(value: str | None) -> str | None:
    """Normalize Unicode casing and whitespace without inventing a missing value."""

    if value is None:
        return None

    candidate = unicodedata.normalize("NFKC", value).casefold()
    normalized = " ".join(candidate.split())
    return normalized or None


def normalize_platform(value: str | None) -> str | None:
    """Normalize known platform labels for exact comparison."""

    normalized = normalize_text(value)
    return normalized.replace(" ", "_") if normalized is not None else None


def normalize_platform_account_id(value: str | None) -> str | None:
    """Normalize account identifiers without deriving them from URLs or profiles."""

    return normalize_text(value)


def normalize_identity(candidate: LeadIdentityInput) -> NormalizedLeadIdentity:
    """Normalize all deduplication keys from a supplied candidate identity."""

    return NormalizedLeadIdentity(
        canonical_url=normalize_url(candidate.source_url),
        platform=normalize_platform(candidate.platform),
        platform_account_id=normalize_platform_account_id(candidate.platform_account_id),
        normalized_email=normalize_email(candidate.email),
        normalized_phone=normalize_phone(candidate.phone, candidate.country),
        normalized_name=normalize_business_name(candidate.name),
        normalized_city=normalize_text(candidate.city),
    )
