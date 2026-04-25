# network.py — Non-blocking HTTP client (Skill 4)
# =========================================================================
# Fires the POST request on a daemon thread so the Qt event loop is NEVER
# blocked.  In MOCK_MODE it reads mock_response.json instead.

import json
import threading
import time
from pathlib import Path
from typing import Callable

import requests

from constants import BACKEND_URL, MOCK_MODE, REQUEST_TIMEOUT_S

# Path to the local mock file (sibling of this module)
_MOCK_FILE = Path(__file__).parent / "mock_response.json"


def _load_mock() -> dict:
    """Return the Phase-1 hardcoded dummy response."""
    with _MOCK_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _post_worker(
    payload: dict,
    on_success: Callable[[dict], None],
    on_error: Callable[[str], None],
) -> None:
    """
    Worker executed on a background daemon thread.
    Calls on_success(data) or on_error(message) — both are Qt-signal emitters
    that are thread-safe to call from here.
    """
    if MOCK_MODE:
        # Simulate a small network round-trip latency for realism
        time.sleep(0.6)
        on_success(_load_mock())
        return

    try:
        resp = requests.post(
            BACKEND_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()

        # Validate the immutable contract keys
        required = {"status", "ui_directive", "ai_output", "function_triggered"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Response missing contract keys: {missing}")

        on_success(data)

    except requests.exceptions.ConnectionError:
        on_error(
            "⚠️  Cannot reach the AI backend.\n"
            "Make sure Dev B's FastAPI server is running on localhost:8000."
        )
    except requests.exceptions.Timeout:
        on_error(
            f"⚠️  Backend did not respond within {REQUEST_TIMEOUT_S} s.\n"
            "The Gemini API may be rate-limited. Try again shortly."
        )
    except Exception as exc:  # noqa: BLE001
        on_error(f"⚠️  Unexpected error:\n{exc}")


def send_async(
    trigger_type: str,
    screen_b64: str,
    audio_transcript: str,
    on_success: Callable[[dict], None],
    on_error: Callable[[str], None],
) -> threading.Thread:
    """
    Build the JSON contract payload and fire the POST on a daemon thread.

    Parameters
    ----------
    trigger_type : str
        "gesture_pinch" | "keyboard_hotkey"
    screen_b64 : str
        Base64-encoded JPEG of the current screen.
    audio_transcript : str
        Speech-to-text string (empty string if not available).
    on_success : Callable[[dict], None]
        Called with the parsed response dict on HTTP 200.
    on_error : Callable[[str], None]
        Called with a human-readable error string on failure.

    Returns
    -------
    threading.Thread
        The daemon thread (already started).
    """
    payload = {
        "trigger_type": trigger_type,
        "screen_b64": screen_b64,
        "audio_transcript": audio_transcript,
    }

    t = threading.Thread(
        target=_post_worker,
        args=(payload, on_success, on_error),
        daemon=True,
        name="SIE-NetworkWorker",
    )
    t.start()
    return t
