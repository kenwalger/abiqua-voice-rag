import asyncio
import logging
import sys
import time
import traceback
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.pipeline_log import log as pipe_log
from app.rime import get_voices, synthesize
from app.settings import get_settings


@lru_cache(maxsize=1)
def _run_query_fn():
    """Defer importing orchestrator (Mongo + LlamaIndex) until first /query — keeps /voices fast."""
    from app.orchestrator import run_query

    return run_query


logger = logging.getLogger(__name__)
settings = get_settings()


def _configure_logging_early() -> None:
    """Ensure stderr logging works even when uvicorn configures logging first."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    try:
        logging.basicConfig(
            level=level,
            format="%(levelname)s [%(name)s] %(message)s",
            force=True,
        )
    except TypeError:
        logging.basicConfig(
            level=level,
            format="%(levelname)s [%(name)s] %(message)s",
        )
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger.setLevel(level)
    if settings.PIPELINE_DEBUG:
        _pl = logging.getLogger("abiqua.pipeline")
        _pl.setLevel(logging.INFO)
        if not _pl.handlers:
            _h = logging.StreamHandler(sys.stderr)
            _h.setFormatter(
                logging.Formatter("%(levelname)s [%(name)s] %(message)s"),
            )
            _pl.addHandler(_h)
        _pl.propagate = False


_configure_logging_early()


def _public_error_detail(exc: BaseException) -> str | list[Any]:
    if settings.EXPOSE_INTERNAL_ERRORS:
        return f"{type(exc).__name__}: {exc}"
    return "An unexpected error occurred."


VOICES_CACHE: dict[str, Any] = {"expires_at": 0.0, "data": {"voices": []}}
VOICES_CACHE_TTL_SECONDS = 300


def cors_headers_for_request(request: Request) -> dict[str, str]:
    """Mirror CORSMiddleware ACAO so error bodies are readable from the browser."""
    origin = request.headers.get("origin")
    if not origin or origin not in settings.ALLOWED_ORIGINS:
        return {}
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-credentials": "false",
    }


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    voice_id: str | None = None
    voice_model_id: str | None = Field(
        default=None,
        description="Rime model (e.g. mist, arcana). Must match the selected voice id.",
    )
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class ImageRef(BaseModel):
    image_id: str
    url: str
    caption: str | None
    primary: bool


class SourceMeta(BaseModel):
    model: str
    serial_range: str
    year_start: int | None
    year_end: int | None
    record_count: int
    confidence: float


class QueryResponse(BaseModel):
    narration_text: str
    audio_b64: str
    audio_mime: str
    image_count: int
    image_refs: list[ImageRef]
    source_meta: SourceMeta
    query_type: str
    collections_hit: list[str]
    query_echo: str
    latency_ms: int
    record_url: str | None = None


class VoicesResponse(BaseModel):
    voices: list[dict[str, Any]]


class ApiError(BaseModel):
    ok: bool = False
    status: int
    error: str
    detail: Any


@asynccontextmanager
async def lifespan(_: FastAPI):
    _configure_logging_early()
    from app.orchestrator import initialize_retrievers

    try:
        await asyncio.to_thread(initialize_retrievers)
    except Exception as exc:
        logger.warning("initialize_retrievers failed (degraded): %s", exc)
    yield


app = FastAPI(
    title="Abiqua Collection Voice RAG API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def error_envelope_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException as exc:
        payload = ApiError(
            status=exc.status_code,
            error="http_error",
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(),
            headers=cors_headers_for_request(request),
        )
    except Exception as exc:
        logger.exception("Unhandled error in error_envelope_middleware")
        traceback.print_exc(file=sys.stderr)
        payload = ApiError(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="internal_server_error",
            detail=_public_error_detail(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(),
            headers=cors_headers_for_request(request),
        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Route exceptions never reach HTTP middleware; log here so the terminal shows the cause."""
    logger.exception("Unhandled exception during request")
    traceback.print_exc(file=sys.stderr)
    payload = ApiError(
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="internal_server_error",
        detail=_public_error_detail(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(),
        headers=cors_headers_for_request(request),
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    logger.exception("response_model_validation_failed")
    detail: str | list[Any]
    if settings.EXPOSE_INTERNAL_ERRORS:
        detail = exc.errors()
    else:
        detail = "Response validation failed"
    payload = ApiError(
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="response_validation_error",
        detail=detail,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload.model_dump(),
        headers=cors_headers_for_request(request),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    payload = ApiError(
        status=status.HTTP_400_BAD_REQUEST,
        error="validation_error",
        detail=exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=payload.model_dump(),
        headers=cors_headers_for_request(request),
    )


# Registered after custom HTTP middleware so CORS wraps all responses (including
# JSON from error_envelope_middleware) — otherwise some error paths lack ACAO.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def ping_atlas() -> str:
    try:
        from app.orchestrator import mongo_client

        await asyncio.to_thread(mongo_client.admin.command, "ping")
        return "ok"
    except Exception as e:
        logging.getLogger(__name__).warning("Atlas ping failed: %s", e)
        return "unreachable"


async def ping_rime() -> str:
    try:
        import urllib.request
        import urllib.error

        from app.settings import get_settings

        settings = get_settings()
        req = urllib.request.Request(
            f"{settings.RIME_BASE_URL}/v1/voices",
            headers={"Authorization": f"Bearer {settings.RIME_API_KEY}"},
            method="HEAD",
        )

        def _do_head():
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status

        try:
            status_code = await asyncio.to_thread(_do_head)
        except urllib.error.HTTPError as e:
            status_code = e.code
        return "ok" if status_code < 500 else "unreachable"
    except Exception as e:
        logging.getLogger(__name__).warning("Rime ping failed: %s", e)
        return "unreachable"


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(payload: QueryRequest):
    start_time = time.time()
    if settings.PIPELINE_DEBUG:
        print(
            f"[debug] entered /query query='{payload.query[:80]}' top_k={payload.top_k}",
            flush=True,
        )
    pipe_log(
        "/query start q_preview=%s voice_id=%s voice_model_id=%s top_k=%s",
        (payload.query[:120] + "…") if len(payload.query) > 120 else payload.query,
        payload.voice_id,
        payload.voice_model_id,
        payload.top_k,
    )

    t_rag = time.perf_counter()
    try:
        rag_result = await _run_query_fn()(payload.query, payload.top_k)
    except RuntimeError as exc:
        if str(exc) == "retrievers_not_initialized":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        raise
    pipe_log(
        "/query rag_complete elapsed_ms=%.1f query_type=%s chunks_collections=%s",
        (time.perf_counter() - t_rag) * 1000,
        rag_result.query_type,
        rag_result.collections_hit,
    )
    try:
        t_tts = time.perf_counter()
        tts_result = await synthesize(
            rag_result.narration_text,
            payload.voice_id,
            payload.voice_model_id,
        )
        pipe_log(
            "/query tts_complete elapsed_ms=%.1f speaker=%s model=%s audio_b64_len=%s",
            (time.perf_counter() - t_tts) * 1000,
            tts_result.speaker,
            tts_result.model_id,
            len(tts_result.audio_b64),
        )
    except RuntimeError as exc:
        message = str(exc)
        pipe_log("/query tts_failed %s", message[:500])
        logger.warning("rime_synthesize_failed: %s", message)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        ) from exc

    latency_ms = int((time.time() - start_time) * 1000)

    return QueryResponse(
        narration_text=rag_result.narration_text,
        audio_b64=tts_result.audio_b64,
        audio_mime=tts_result.audio_mime,
        image_count=rag_result.image_count,
        image_refs=rag_result.image_refs,
        source_meta=SourceMeta(
            model=rag_result.source_meta.get("model", "Unknown"),
            serial_range=rag_result.source_meta.get("serial_range", "Unknown"),
            year_start=rag_result.source_meta.get("year_start"),
            year_end=rag_result.source_meta.get("year_end"),
            record_count=int(rag_result.source_meta.get("record_count", 0)),
            confidence=float(rag_result.source_meta.get("confidence", 0.0)),
        ),
        query_type=rag_result.query_type,
        collections_hit=rag_result.collections_hit,
        query_echo=payload.query,
        latency_ms=latency_ms,
        record_url=rag_result.record_url,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/ready")
async def ready() -> JSONResponse:
    atlas_status, rime_status = await asyncio.gather(
        ping_atlas(),
        ping_rime(),
    )
    overall = "ready" if atlas_status == "ok" and rime_status == "ok" else "degraded"
    status_code = status.HTTP_200_OK if overall == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "atlas": atlas_status,
            "rime": rime_status,
        },
    )


@app.get("/voices", response_model=VoicesResponse)
async def voices() -> VoicesResponse:
    now = time.time()
    t_req = time.perf_counter()
    if settings.PIPELINE_DEBUG:
        print("[debug] entered /voices", flush=True)
    if VOICES_CACHE["expires_at"] > now:
        n = len(VOICES_CACHE["data"].get("voices", []))
        pipe_log("GET /voices cache_hit voices=%s elapsed_ms=%.1f", n, (time.perf_counter() - t_req) * 1000)
        return VoicesResponse(voices=VOICES_CACHE["data"]["voices"])

    pipe_log("GET /voices cache_miss fetching")
    try:
        voices_data = await get_voices()
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("rime_api_error:") or message.startswith("rime_unreachable:"):
            # Degraded mode: keep 200 so the UI loads; TTS still uses RIME_DEFAULT_VOICE.
            logger.warning("voices_unavailable_using_empty_list: %s", message)
            pipe_log(
                "GET /voices degraded_empty_list reason=%s elapsed_ms=%.1f",
                message[:200],
                (time.perf_counter() - t_req) * 1000,
            )
            return VoicesResponse(voices=[])
        pipe_log("GET /voices error %s", message[:300])
        raise

    raw_list = voices_data.get("voices", [])
    VOICES_CACHE["data"] = voices_data
    VOICES_CACHE["expires_at"] = now + VOICES_CACHE_TTL_SECONDS
    pipe_log(
        "GET /voices ok voices=%s elapsed_ms=%.1f",
        len(raw_list),
        (time.perf_counter() - t_req) * 1000,
    )
    return VoicesResponse(voices=raw_list)

