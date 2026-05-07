import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.orchestrator import run_query
from app.rime import get_voices, synthesize
from app.settings import get_settings

settings = get_settings()
VOICES_CACHE: dict[str, Any] = {"expires_at": 0.0, "data": {"voices": []}}
VOICES_CACHE_TTL_SECONDS = 300


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    voice_id: str | None = None
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


class VoicesResponse(BaseModel):
    voices: list[dict[str, Any]]


class ApiError(BaseModel):
    ok: bool = False
    status: int
    error: str
    detail: Any


app = FastAPI(title="Abiqua Collection Voice RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())
    except Exception:
        payload = ApiError(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="internal_server_error",
            detail="An unexpected error occurred.",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(),
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    _ = request
    payload = ApiError(
        status=status.HTTP_400_BAD_REQUEST,
        error="validation_error",
        detail=exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=payload.model_dump(),
    )


async def ping_atlas() -> str:
    return "ok"


async def ping_rime() -> str:
    return "ok"


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(payload: QueryRequest):
    start_time = time.time()

    rag_result = await run_query(payload.query, payload.top_k)
    try:
        tts_result = await synthesize(rag_result.narration_text, payload.voice_id)
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("rime_api_error:") or message.startswith("rime_unreachable:"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=message,
            ) from exc
        raise

    latency_ms = int((time.time() - start_time) * 1000)

    return QueryResponse(
        narration_text=rag_result.narration_text,
        audio_b64=tts_result.audio_b64,
        audio_mime=tts_result.audio_mime,
        image_count=rag_result.image_count,
        image_refs=rag_result.image_refs,
        source_meta=rag_result.source_meta,
        query_type=rag_result.query_type,
        collections_hit=rag_result.collections_hit,
        query_echo=payload.query,
        latency_ms=latency_ms,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/ready")
async def ready() -> JSONResponse:
    atlas_status = await ping_atlas()
    rime_status = await ping_rime()

    if atlas_status == "ok" and rime_status == "ok":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "atlas": "ok", "rime": "ok"},
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "degraded", "atlas": atlas_status, "rime": rime_status},
    )


@app.get("/voices", response_model=VoicesResponse)
async def voices() -> VoicesResponse:
    now = time.time()
    if VOICES_CACHE["expires_at"] > now:
        return VoicesResponse(voices=VOICES_CACHE["data"]["voices"])

    try:
        voices_data = await get_voices()
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("rime_api_error:") or message.startswith("rime_unreachable:"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=message,
            ) from exc
        raise

    VOICES_CACHE["data"] = voices_data
    VOICES_CACHE["expires_at"] = now + VOICES_CACHE_TTL_SECONDS
    return VoicesResponse(voices=voices_data.get("voices", []))

