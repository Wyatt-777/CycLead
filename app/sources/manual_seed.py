"""A local JSON source adapter for user-supplied, publicly verifiable seed records."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError, field_validator

from app.schemas.inputs import InputModel, validate_public_url
from app.sources.base import RawCandidateData, SourceDiscoveryResult, SourceRecordError


class ManualSeedFileError(ValueError):
    """The seed file itself cannot be opened or interpreted as a candidate collection."""


class ManualSeedRecord(InputModel):
    """One validated manual seed record before it becomes a source candidate."""

    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snippet: str | None = None
    captured_at: datetime | None = None
    name: str | None = Field(default=None, max_length=500)
    description: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    website: str | None = None
    social_url: str | None = None
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    raw_contact_text: str | None = None
    services: list[str] = Field(default_factory=list)

    validate_url = field_validator("url")(validate_public_url)
    validate_website = field_validator("website")(validate_public_url)
    validate_social_url = field_validator("social_url")(validate_public_url)

    @field_validator("captured_at")
    @classmethod
    def require_timezone_when_provided(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("captured_at must include a timezone offset")
        return value

    @field_validator("services")
    @classmethod
    def reject_blank_services(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("services cannot contain blank values")
        return values


class ManualSeedSource:
    """Load a local manual-seed JSON file without any network requests."""

    source_name = "manual_seed"

    def __init__(self, path: Path) -> None:
        self._path = path

    def discover(self) -> SourceDiscoveryResult:
        """Convert valid records and retain per-record validation errors for the run report."""

        raw_records = self._load_records()
        result = SourceDiscoveryResult()

        for index, raw_record in enumerate(raw_records):
            try:
                record = ManualSeedRecord.model_validate(raw_record)
            except ValidationError as error:
                result.errors.append(SourceRecordError(record_index=index, message=str(error)))
                continue

            result.candidates.append(
                RawCandidateData(
                    source=self.source_name,
                    url=record.url,
                    title=record.title,
                    snippet=record.snippet,
                    captured_at=record.captured_at or datetime.now(timezone.utc),
                    name=record.name,
                    description=record.description,
                    country=record.country,
                    city=record.city,
                    website=record.website,
                    social_url=record.social_url,
                    email=record.email,
                    phone=record.phone,
                    raw_contact_text=record.raw_contact_text,
                    services=record.services,
                )
            )

        return result

    def _load_records(self) -> list[Any]:
        try:
            contents = self._path.read_text(encoding="utf-8")
        except OSError as error:
            raise ManualSeedFileError(f"cannot read seed file: {self._path}") from error

        try:
            payload = json.loads(contents)
        except json.JSONDecodeError as error:
            raise ManualSeedFileError("seed file is not valid JSON") from error

        if isinstance(payload, dict):
            payload = payload.get("candidates")

        if not isinstance(payload, list):
            raise ManualSeedFileError(
                "seed file must be an array or an object with a candidates array"
            )
        return payload
