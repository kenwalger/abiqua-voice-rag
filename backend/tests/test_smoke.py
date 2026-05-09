"""Lightweight imports so `uv run pytest` exercises the project's venv, not global pytest plugins."""

import os

import pytest

REQUIRED_ENV_VARS = [
    "MONGODB_URI",
    "ANTHROPIC_API_KEY",
    "RIME_API_KEY",
    "OPENAI_API_KEY",
]


def test_fastapi_app_metadata() -> None:
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        pytest.skip(
            f"Smoke test requires env vars: {', '.join(missing)}",
        )
    from app.main import app

    assert app.title
    assert app.version == "1.0.0"
