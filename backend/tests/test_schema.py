import pytest
from pydantic import ValidationError

from app.main import (
    ApiError,
    CognitiveBudget,
    ImageRef as BackendImageRef,
    QueryRequest,
    QueryResponse,
    SourceMeta,
)
from app.settings import get_settings


def make_source_meta(**kwargs: object) -> SourceMeta:
    defaults: dict[str, object] = {
        "model": ".32 New Departure",
        "serial_range": "143960",
        "year_start": 1905,
        "year_end": None,
        "record_count": 1,
        "confidence": 1.0,
    }
    return SourceMeta(**{**defaults, **kwargs})


def make_cost_estimate(**kwargs: object) -> CognitiveBudget:
    defaults: dict[str, object] = {
        "embedding_tokens": 8,
        "narration_input_tokens": 312,
        "narration_output_tokens": 89,
        "tts_characters": 387,
        "collections_queried": 1,
        "routing_decision": "serial_number",
        "narration_model": "claude-haiku-4-5-20251001",
        "embedding_cost_usd": 0.00000016,
        "narration_cost_usd": 0.00060560,
        "tts_cost_usd": 0.00619200,
        "total_cost_usd": 0.00679776,
        "daily_cost_at_10k_usd": 67.9776,
        "pricing_date": "2026-05-01",
    }
    return CognitiveBudget(**{**defaults, **kwargs})


def _base_response(**kwargs: object) -> QueryResponse:
    base: dict[str, object] = {
        "narration_text": "Test.",
        "audio_b64": "dGVzdA==",
        "audio_mime": "audio/mpeg",
        "image_count": 0,
        "image_refs": [],
        "source_meta": make_source_meta(),
        "query_type": "serial_number",
        "collections_hit": ["firearms_direct_lookup"],
        "query_echo": "143960",
        "latency_ms": 1200,
        "record_url": None,
        "cognitive_budget": make_cost_estimate(),
    }
    return QueryResponse(**{**base, **kwargs})


class TestQueryRequest:
    def test_valid_query_only(self) -> None:
        req = QueryRequest(query="143960")
        assert req.query == "143960"
        assert req.top_k == 5

    def test_valid_with_all_fields(self) -> None:
        req = QueryRequest(query="New Departure", voice_id="colby", top_k=10)
        assert req.voice_id == "colby"
        assert req.top_k == 10

    def test_rejects_short_query(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(query="x")

    def test_rejects_long_query(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(query="x" * 501)

    def test_rejects_top_k_over_max(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(query="143960", top_k=21)


class TestQueryResponse:
    def test_null_year_end(self) -> None:
        resp = _base_response()
        assert resp.source_meta.year_end is None

    def test_empty_image_refs(self) -> None:
        resp = _base_response(
            source_meta=make_source_meta(year_start=None),
            query_echo="test",
            latency_ms=100,
            collections_hit=[],
        )
        assert resp.image_refs == []

    def test_backend_imageref_null_caption(self) -> None:
        ref = BackendImageRef(
            image_id="abc123",
            url="https://example.com/img.webp",
            caption=None,
            primary=True,
        )
        assert ref.caption is None

    def test_source_meta_all_null_years(self) -> None:
        meta = make_source_meta(year_start=None, year_end=None)
        assert meta.year_start is None
        assert meta.year_end is None

    def test_api_error_shape(self) -> None:
        err = ApiError(
            ok=False,
            status=422,
            error="no_records_found",
            detail="No matching records.",
        )
        assert err.ok is False

    def test_record_url_valid(self) -> None:
        url = "https://theabiquacollection.com/f/fbGhMSuH"
        resp = _base_response(
            query_echo="test",
            latency_ms=100,
            record_url=url,
        )
        assert resp.record_url == url

    def test_record_url_null(self) -> None:
        resp = _base_response(query_echo="test", latency_ms=100, record_url=None)
        assert resp.record_url is None

    def test_expose_internal_errors_default(self) -> None:
        settings = get_settings()
        assert settings.EXPOSE_INTERNAL_ERRORS is False

    def test_cognitive_budget_model(self) -> None:
        budget = make_cost_estimate()
        assert budget.routing_decision == "serial_number"
        assert budget.collections_queried == 1
        assert budget.total_cost_usd > 0
