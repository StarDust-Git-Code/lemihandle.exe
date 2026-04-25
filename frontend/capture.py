# capture.py — Screen capture + Base64 encode (Skill 3)
# =========================================================================
# Grabs the full primary monitor in < 0.5 s and returns a base64 string
# ready to be injected into the JSON contract.  Never writes to disk.

import io
import base64
import time

import mss
import mss.tools
from PIL import Image


def capture_screen_b64() -> str:
    """
    Capture the primary monitor and return a base64-encoded JPEG string.

    Returns
    -------
    str
        Base64-encoded bytes of the screenshot (JPEG, quality=75).

    Raises
    ------
    RuntimeError
        If the capture takes longer than 500 ms (safety guard per spec).
    """
    t0 = time.monotonic()

    with mss.mss() as sct:
        monitor = sct.monitors[1]          # monitors[0] = all combined; [1] = primary
        raw = sct.grab(monitor)            # BGRA raw buffer, no disk I/O

    # Convert BGRA → RGB via Pillow
    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    # Encode to JPEG in-memory
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75, optimize=True)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")

    elapsed_ms = (time.monotonic() - t0) * 1000
    if elapsed_ms > 500:
        raise RuntimeError(
            f"Screen capture exceeded 500 ms budget (took {elapsed_ms:.1f} ms)"
        )

    return b64
