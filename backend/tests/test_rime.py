import asyncio
import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from urllib.error import HTTPError, URLError

from app.rime import (
    DEFAULT_VOICE,
    RimeResult,
    _clean_narration,
    get_voices,
    synthesize,
)

FAKE_MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 100


def make_mock_response(body: bytes) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = body
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestSynthesize:
    def test_returns_rime_result(self) -> None:
        async def _run() -> RimeResult:
            with patch(
                "urllib.request.urlopen",
                return_value=make_mock_response(FAKE_MP3),
            ):
                return await synthesize("The New Departure was produced in 1887.")

        result = asyncio.run(_run())
        assert isinstance(result, RimeResult)
        assert result.audio_mime == "audio/mpeg"
        assert result.char_count > 0

    def test_audio_b64_round_trips(self) -> None:
        async def _run() -> RimeResult:
            with patch(
                "urllib.request.urlopen",
                return_value=make_mock_response(FAKE_MP3),
            ):
                return await synthesize("Test.")

        result = asyncio.run(_run())
        raw = base64.b64decode(result.audio_b64)
        assert raw.startswith(b"ID3")
        assert raw.endswith(FAKE_MP3)

    def test_uses_default_voice(self) -> None:
        async def _run() -> RimeResult:
            with patch(
                "urllib.request.urlopen",
                return_value=make_mock_response(FAKE_MP3),
            ):
                return await synthesize("Test.", speaker=None)

        result = asyncio.run(_run())
        assert result.speaker == DEFAULT_VOICE

    def test_uses_provided_speaker(self) -> None:
        async def _run() -> RimeResult:
            with patch(
                "urllib.request.urlopen",
                return_value=make_mock_response(FAKE_MP3),
            ):
                return await synthesize("Test.", speaker="grove")

        result = asyncio.run(_run())
        assert result.speaker == "grove"

    def test_401_raises_api_error(self) -> None:
        fp = BytesIO(b'{"error": "invalid_api_key"}')
        err = HTTPError("", 401, "Unauthorized", MagicMock(), fp)

        async def _run() -> None:
            with patch("urllib.request.urlopen", side_effect=err):
                await synthesize("Test.")

        with pytest.raises(RuntimeError) as exc:
            asyncio.run(_run())
        assert "rime_api_error:401" in str(exc.value)

    def test_429_raises_api_error(self) -> None:
        fp = BytesIO(b'{"error": "rate_limit"}')
        err = HTTPError("", 429, "Too Many Requests", MagicMock(), fp)

        async def _run() -> None:
            with patch("urllib.request.urlopen", side_effect=err):
                await synthesize("Test.")

        with pytest.raises(RuntimeError) as exc:
            asyncio.run(_run())
        assert "rime_api_error:429" in str(exc.value)

    def test_url_error_raises_unreachable(self) -> None:
        async def _run() -> None:
            with patch(
                "urllib.request.urlopen",
                side_effect=URLError("Connection refused"),
            ):
                await synthesize("Test.")

        with pytest.raises(RuntimeError) as exc:
            asyncio.run(_run())
        assert "rime_unreachable" in str(exc.value)


class TestCleanNarration:
    def test_strips_underscores(self) -> None:
        result = _clean_narration("_Shipped_ in 1905.")
        assert "_" not in result
        assert "Shipped" in result

    def test_strips_bold_asterisks(self) -> None:
        result = _clean_narration("**factory letter** on file.")
        assert "*" not in result
        assert "factory letter" in result

    def test_strips_markdown_links(self) -> None:
        result = _clean_narration("[view record](https://example.com)")
        assert "view record" in result
        assert "https://example.com" not in result

    def test_preserves_bare_urls(self) -> None:
        url = "https://theabiquacollection.com/f/fbGhMSuH"
        result = _clean_narration(f"View at {url}")
        assert url in result


class TestGetVoices:
    def test_returns_voice_list(self) -> None:
        fake = [{"id": "colby", "name": "Colby", "preview_url": None}]
        mock_resp = make_mock_response(json.dumps(fake).encode())

        async def _run() -> dict:
            with patch("urllib.request.urlopen", return_value=mock_resp):
                return await get_voices()

        result = asyncio.run(_run())
        assert result == {"voices": fake}

    def test_raises_on_network_failure(self) -> None:
        async def _run() -> None:
            with patch(
                "urllib.request.urlopen",
                side_effect=URLError("Name resolution failed"),
            ):
                await get_voices()

        with pytest.raises(RuntimeError):
            asyncio.run(_run())
