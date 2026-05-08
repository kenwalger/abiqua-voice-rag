"""Opt-in verbose logging for `/voices`, retrieval, and `/query`. Set PIPELINE_DEBUG=true in backend/.env."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator

from app.settings import get_settings

_logger = logging.getLogger("abiqua.pipeline")


def enabled() -> bool:
    return bool(get_settings().PIPELINE_DEBUG)


def log(msg: str, *args: Any) -> None:
    if not enabled():
        return
    _logger.info("[pipeline] " + msg, *args)


@contextmanager
def timed(step: str, **fields: Any) -> Iterator[None]:
    if not enabled():
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t0) * 1000
        extra = (" " + repr(fields)) if fields else ""
        _logger.info("[pipeline] %s finished in %.1fms%s", step, ms, extra)


@asynccontextmanager
async def timed_async(step: str, **fields: Any) -> AsyncIterator[None]:
    if not enabled():
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t0) * 1000
        extra = (" " + repr(fields)) if fields else ""
        _logger.info("[pipeline] %s finished in %.1fms%s", step, ms, extra)
