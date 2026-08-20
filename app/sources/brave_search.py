"""Official Brave Search API adapter for small, compliant public-web discovery runs."""

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import Field, ValidationError, field_validator

from app.schemas.inputs import InputModel, validate_public_url
from app.sources.base import (
    RawCandidateData,
    SourceDiscoveryError,
    SourceDiscoveryResult,
    SourceRecordError,
)

BRAVE_WEB_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
MAX_QUERY_CHARACTERS = 400
MAX_QUERY_WORDS = 50


class BraveSearchConfigurationError(ValueError):
    """The local Brave Search source configuration is missing or invalid."""


class BraveSearchRequestError(SourceDiscoveryError):
    """The official Brave API could not return a usable search response."""


class BraveSearchResponseError(SourceDiscoveryError):
    """The Brave API response was not shaped like a web-search response."""


class BraveSearchResult(InputModel):
    """The subset of one web result that CycleLead retains as raw public evidence."""

    url: str = Field(min_length=1)
    title: str = Field(min_length=1)
    snippet: str | None = None

    validate_url = field_validator("url")(validate_public_url)


class BraveSearchSource:
    """Fetch a bounded set of API-provided web results without visiting result pages."""

    source_name = "brave_search"

    def __init__(
        self,
        *,
        query: str,
        api_key: str | None,
        country: str = "US",
        search_language: str = "en",
        result_count: int = 10,
        timeout_seconds: float = 10,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._query = self._validate_query(query)
        self._api_key = self._validate_api_key(api_key)
        self._country = self._validate_country(country)
        self._search_language = self._validate_language(search_language)
        self._result_count = self._validate_result_count(result_count)
        self._timeout_seconds = timeout_seconds
        if timeout_seconds <= 0:
            raise BraveSearchConfigurationError("Brave Search timeout must be greater than zero")
        self._http_client = http_client

    def discover(self) -> SourceDiscoveryResult:
        """Call the documented API once and retain only result URL, title, and description."""

        response = self._get_response()
        payload = self._decode_response(response)
        return self._candidates_from_payload(payload)

    def _get_response(self) -> httpx.Response:
        if self._http_client is not None:
            return self._request(self._http_client)

        with httpx.Client(timeout=self._timeout_seconds, follow_redirects=False) as client:
            return self._request(client)

    def _request(self, client: httpx.Client) -> httpx.Response:
        try:
            response = client.get(
                BRAVE_WEB_SEARCH_URL,
                params={
                    "q": self._query,
                    "country": self._country,
                    "search_lang": self._search_language,
                    "count": self._result_count,
                    "safesearch": "moderate",
                },
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._api_key,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise BraveSearchRequestError(
                f"Brave Search API returned HTTP {error.response.status_code}"
            ) from error
        except httpx.RequestError as error:
            raise BraveSearchRequestError(
                f"Brave Search request failed: {type(error).__name__}"
            ) from error
        return response

    @staticmethod
    def _decode_response(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except json.JSONDecodeError as error:
            raise BraveSearchResponseError("Brave Search API response is not valid JSON") from error
        if not isinstance(payload, dict):
            raise BraveSearchResponseError("Brave Search API response must be a JSON object")
        return payload

    def _candidates_from_payload(self, payload: dict[str, Any]) -> SourceDiscoveryResult:
        web = payload.get("web")
        if web is None:
            return SourceDiscoveryResult()
        if not isinstance(web, dict):
            raise BraveSearchResponseError("Brave Search API web response must be an object")

        records = web.get("results", [])
        if records is None:
            return SourceDiscoveryResult()
        if not isinstance(records, list):
            raise BraveSearchResponseError("Brave Search API web results must be an array")

        captured_at = datetime.now(timezone.utc)
        discovery_result = SourceDiscoveryResult()
        for index, raw_record in enumerate(records):
            try:
                if not isinstance(raw_record, dict):
                    raise ValueError("web result must be an object")
                record = BraveSearchResult(
                    url=raw_record.get("url"),
                    title=raw_record.get("title"),
                    snippet=raw_record.get("description"),
                )
            except (ValidationError, ValueError) as error:
                discovery_result.errors.append(
                    SourceRecordError(record_index=index, message=str(error))
                )
                continue

            discovery_result.candidates.append(
                RawCandidateData(
                    source=self.source_name,
                    url=record.url,
                    title=record.title,
                    snippet=record.snippet,
                    captured_at=captured_at,
                )
            )
        return discovery_result

    @staticmethod
    def _validate_api_key(api_key: str | None) -> str:
        if api_key is None or not api_key.strip():
            raise BraveSearchConfigurationError(
                "CYCLELEAD_BRAVE_SEARCH_API_KEY is required for source brave_search"
            )
        return api_key.strip()

    @staticmethod
    def _validate_query(query: str) -> str:
        normalized_query = query.strip()
        if not normalized_query:
            raise BraveSearchConfigurationError("Brave Search query cannot be blank")
        if len(normalized_query) > MAX_QUERY_CHARACTERS:
            raise BraveSearchConfigurationError(
                f"Brave Search query cannot exceed {MAX_QUERY_CHARACTERS} characters"
            )
        if len(normalized_query.split()) > MAX_QUERY_WORDS:
            raise BraveSearchConfigurationError(
                f"Brave Search query cannot exceed {MAX_QUERY_WORDS} words"
            )
        return normalized_query

    @staticmethod
    def _validate_country(country: str) -> str:
        normalized_country = country.strip().upper()
        if (
            len(normalized_country) != 2
            or not normalized_country.isascii()
            or not normalized_country.isalpha()
        ):
            raise BraveSearchConfigurationError("Brave Search country must be a two-letter code")
        return normalized_country

    @staticmethod
    def _validate_language(search_language: str) -> str:
        normalized_language = search_language.strip()
        if not normalized_language:
            raise BraveSearchConfigurationError("Brave Search language cannot be blank")
        return normalized_language

    @staticmethod
    def _validate_result_count(result_count: int) -> int:
        if not 1 <= result_count <= 20:
            raise BraveSearchConfigurationError(
                "Brave Search result count must be between 1 and 20"
            )
        return result_count
