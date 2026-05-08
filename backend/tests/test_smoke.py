"""Lightweight imports so `uv run pytest` exercises the project's venv, not global pytest plugins."""

def test_fastapi_app_metadata() -> None:
    from app.main import app

    assert app.title
    assert app.version == "1.0.0"
