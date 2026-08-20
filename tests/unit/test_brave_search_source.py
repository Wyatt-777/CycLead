"""Tests for the bounded official Brave Search API source adapter."""

import httpx
import pytest

from app.sources import (
    BraveSearchConfigurationError,
    BraveSearchRequestError,
    BraveSearchResponseError,
    BraveSearchSource,
)


def test_brave_search_source_retains_valid_public_results_and_record_errors() -> None:
    observed_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed_requests.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "url": "https://example.test/studio",
                            "title": "Example Bike Studio",
                            "description": "Custom bike builds and upgrades.",
                        },
                        {"url": "mailto:invalid@example.test", "title": "Invalid URL"},
                    ]
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = BraveSearchSource(
            query="bike workshop",
            api_key="test-token",
            country="sg",
            search_language="en",
            result_count=2,
            timeout_seconds=1,
            http_client=client,
        ).discover()

    request = observed_requests[0]
    assert request.headers["X-Subscription-Token"] == "test-token"
    assert dict(request.url.params) == {
        "q": "bike workshop",
        "country": "SG",
        "search_lang": "en",
        "count": "2",
        "safesearch": "moderate",
    }
    assert result.candidates[0].source == "brave_search"
    assert result.candidates[0].url == "https://example.test/studio"
    assert result.candidates[0].snippet == "Custom bike builds and upgrades."
    assert result.candidates[0].captured_at.tzinfo is not None
    assert result.errors[0].record_index == 1


def test_brave_search_source_handles_empty_and_malformed_api_payloads() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"web": None}))
    ) as client:
        assert BraveSearchSource(
            query="bike repair",
            api_key="test-token",
            http_client=client,
        ).discover().candidates == []

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"web": {"results": {}}})
        )
    ) as client:
        source = BraveSearchSource(
            query="bike repair",
            api_key="test-token",
            http_client=client,
        )
        with pytest.raises(BraveSearchResponseError, match="results must be an array"):
            source.discover()


def test_brave_search_source_reports_request_failures_without_exposing_a_key() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(429, request=request))
    ) as client:
        source = BraveSearchSource(
            query="bike workshop",
            api_key="confidential-token",
            http_client=client,
        )
        with pytest.raises(BraveSearchRequestError, match="HTTP 429") as error:
            source.discover()

    assert "confidential-token" not in str(error.value)


def test_brave_search_source_reports_network_and_invalid_json_failures() -> None:
    def network_failure(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    with httpx.Client(transport=httpx.MockTransport(network_failure)) as client:
        source = BraveSearchSource(
            query="bike workshop",
            api_key="test-token",
            http_client=client,
        )
        with pytest.raises(BraveSearchRequestError, match="ConnectError"):
            source.discover()

    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not json"))
    ) as client:
        source = BraveSearchSource(
            query="bike workshop",
            api_key="test-token",
            http_client=client,
        )
        with pytest.raises(BraveSearchResponseError, match="not valid JSON"):
            source.discover()


def test_brave_search_source_requires_bounded_and_configured_input() -> None:
    with pytest.raises(BraveSearchConfigurationError, match="API_KEY"):
        BraveSearchSource(query="bike workshop", api_key=None)
    with pytest.raises(BraveSearchConfigurationError, match="400 characters"):
        BraveSearchSource(query="x" * 401, api_key="test-token")
    with pytest.raises(BraveSearchConfigurationError, match="between 1 and 20"):
        BraveSearchSource(query="bike workshop", api_key="test-token", result_count=21)
