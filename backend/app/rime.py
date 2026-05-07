import asyncio
import base64
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.settings import get_settings

settings = get_settings()

RIME_BASE_URL = settings.RIME_BASE_URL
RIME_API_URL = f"{RIME_BASE_URL}/v1/rime-tts"
RIME_VOICES_URL = f"{RIME_BASE_URL}/v1/voices"
RIME_VOICES_DATA_URL = f"{RIME_BASE_URL}/data/voices/all-v2.json"
RIME_API_KEY = settings.RIME_API_KEY
DEFAULT_VOICE = settings.RIME_DEFAULT_VOICE
DEFAULT_MODEL = "arcana"
SPEED_ALPHA = 0.95
SAMPLING_RATE = 22050


@dataclass
class RimeResult:
    audio_b64: str
    audio_mime: str
    speaker: str
    model_id: str
    char_count: int


def _clean_narration(text: str) -> str:
    text = re.sub(r"[_*#`]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _ensure_mp3_header(audio_bytes: bytes) -> bytes:
    if audio_bytes.startswith(b"ID3"):
        return audio_bytes
    # Add an empty ID3v2 header so clients that check ID3 can validate MP3.
    return b"ID3\x03\x00\x00\x00\x00\x00\x00" + audio_bytes


async def synthesize(narration_text: str, speaker: str | None = None) -> RimeResult:
    selected_speaker = speaker or DEFAULT_VOICE
    text = _clean_narration(narration_text)

    payload = json.dumps(
        {
            "text": text,
            "speaker": selected_speaker,
            "modelId": DEFAULT_MODEL,
            "speedAlpha": SPEED_ALPHA,
            "samplingRate": SAMPLING_RATE,
            "reduceLatency": False,
        }
    ).encode("utf-8")

    headers = {
        "Accept": "audio/mp3",
        "Authorization": f"Bearer {RIME_API_KEY}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        RIME_API_URL,
        data=payload,
        headers=headers,
        method="POST",
    )

    loop = asyncio.get_event_loop()

    def _do_request() -> bytes:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()

    try:
        audio_bytes = await loop.run_in_executor(None, _do_request)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"rime_api_error:{exc.code}:{body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"rime_unreachable:{exc.reason}") from exc

    audio_bytes = _ensure_mp3_header(audio_bytes)

    return RimeResult(
        audio_b64=base64.b64encode(audio_bytes).decode("utf-8"),
        audio_mime="audio/mpeg",
        speaker=selected_speaker,
        model_id=DEFAULT_MODEL,
        char_count=len(text),
    )


async def get_voices() -> dict[str, Any]:
    loop = asyncio.get_event_loop()

    def _fetch(url: str, method: str, data: bytes | None = None, auth: bool = True) -> Any:
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {RIME_API_KEY}"
        request = urllib.request.Request(
            url,
            headers=headers,
            data=data,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read())

    def _normalize_voices(voices_raw: Any) -> dict[str, Any]:
        if isinstance(voices_raw, dict) and "voices" in voices_raw and isinstance(voices_raw["voices"], list):
            return {"voices": voices_raw["voices"]}
        if isinstance(voices_raw, list):
            return {"voices": voices_raw}
        if isinstance(voices_raw, dict):
            flattened: list[dict[str, Any]] = []
            for model_id, lang_map in voices_raw.items():
                if not isinstance(lang_map, dict):
                    continue
                for voice_ids in lang_map.values():
                    if not isinstance(voice_ids, list):
                        continue
                    for voice_id in voice_ids:
                        flattened.append(
                            {
                                "id": str(voice_id),
                                "name": str(voice_id),
                                "preview_url": None,
                                "model_id": str(model_id),
                            }
                        )
            if flattened:
                return {"voices": flattened}
        return {"voices": []}

    try:
        voices_raw = await loop.run_in_executor(None, _fetch, RIME_VOICES_URL, "GET", None, True)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 400 and "request body is required" in body.lower():
            try:
                voices_raw = await loop.run_in_executor(None, _fetch, RIME_VOICES_URL, "POST", b"{}", True)
            except urllib.error.HTTPError as inner_exc:
                inner_body = inner_exc.read().decode("utf-8", errors="replace")
                if inner_exc.code == 400 and "text is required" in inner_body.lower():
                    try:
                        data_voices = await loop.run_in_executor(
                            None, _fetch, RIME_VOICES_DATA_URL, "GET", None, False
                        )
                    except urllib.error.HTTPError as data_exc:
                        data_body = data_exc.read().decode("utf-8", errors="replace")
                        raise RuntimeError(f"rime_api_error:{data_exc.code}:{data_body}") from data_exc
                    except urllib.error.URLError as data_exc:
                        raise RuntimeError(f"rime_unreachable:{data_exc.reason}") from data_exc
                    return _normalize_voices(data_voices)
                raise RuntimeError(f"rime_api_error:{inner_exc.code}:{inner_body}") from inner_exc
            except urllib.error.URLError as inner_exc:
                raise RuntimeError(f"rime_unreachable:{inner_exc.reason}") from inner_exc
            return _normalize_voices(voices_raw)
        raise RuntimeError(f"rime_api_error:{exc.code}:{body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"rime_unreachable:{exc.reason}") from exc

    return _normalize_voices(voices_raw)
