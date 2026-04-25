# Dev A Walkthrough — Spatial Intent Engine (GEMINI.EXE)

## What Was Built

A full **PyQt5 transparent OS overlay** that acts as the skin layer for the
Spatial Intent Engine, implementing all 5 skills from the Dev A spec.

---

## File Structure

```
lemihandle.exe/
├── main.py              ← Entry point (wiring, hotkey, event loop)
├── overlay.py           ← Transparent window + render engine (Skills 1 & 5)
├── gesture_engine.py    ← MediaPipe QThread (Skill 2 — Path A)
├── capture.py           ← mss screenshot + Base64 (Skill 3)
├── network.py           ← Non-blocking POST thread (Skill 4)
├── constants.py         ← All magic numbers and phase toggles
├── requirements.txt     ← Pinned deps (all successfully installed)
└── mock_response.json   ← Phase 1 dummy AI response
```

---

## Skills Delivered

| Skill | Implementation |
|-------|---------------|
| **1 — Transparency** | `FramelessWindowHint + WA_TranslucentBackground` + `ctypes.SetWindowLong` to inject `WS_EX_TRANSPARENT \| WS_EX_LAYERED` for true click-through |
| **2A — Vision** | `GestureEngine(QThread)` — MediaPipe Hands, Landmark 4/8 Euclidean distance < 20 px → emits `pinch_detected` signal |
| **2B — Keyboard** | `keyboard.add_hotkey('ctrl+shift+space', ...)` registered in `main.py`, bridged to Qt's event queue via `QMetaObject.invokeMethod` |
| **3 — State+Capture** | `capture_screen_b64()` — mss BGRA → Pillow RGB → JPEG → base64, with 500 ms guard; camera paused on trigger |
| **4 — Non-Blocking Net** | `network.send_async()` spawns a `threading.Thread(daemon=True)`; calls `on_success` / `on_error` callbacks which emit Qt signals back to the overlay |
| **5 — Render Engine** | `_OverlayCanvas.paintEvent` — `QPainter` glassmorphism card with neon glow, word-wrapped `QTextDocument` body, `QPropertyAnimation` fade-in, 8-second auto-dismiss |

---

## Phase Execution Guide

### Phase 1 — Mock (Current Default)

```python
# constants.py
MOCK_MODE = True   ← already set
```

```powershell
cd "C:\Users\firex's ideapad\.gemini\antigravity\lemihandle.exe"
python main.py
```

> Press **Ctrl+Shift+Space** — you'll see the processing pill appear,
> then a frosted-glass result card with the mock AI response fade in.
> It auto-dismisses after 8 seconds. **Escape** dismisses early.

---

### Phase 2 — Debounce (Built-in)

Already active. After any trigger fires, a `threading.Event` lock is set.
A `threading.Timer(3.0, release)` clears it after 3 seconds.
Rapid re-triggers within the cooldown are silently logged and dropped.

---

### Phase 3 — Live Integration (When Dev B is Ready)

```python
# constants.py
MOCK_MODE = False  ← flip this one line
```

Start Dev B's FastAPI server (`uvicorn main:app --host 0.0.0.0 --port 8000`),
then run `python main.py` — the full end-to-end Gemini loop is live.

---

## JSON Contract Adherence

Dev A sends exactly:
```json
{
  "trigger_type": "gesture_pinch | keyboard_hotkey",
  "screen_b64": "<base64_jpeg>",
  "audio_transcript": ""
}
```

Dev A expects exactly:
```json
{
  "status": "...",
  "ui_directive": "display_floating_card",
  "ai_output": "...",
  "function_triggered": "..."
}
```

`network.py` validates the four required keys and surfaces a user-visible
error card if any are missing — the contract is treated as immutable.

---

## Notes for Dev B Handoff

- `audio_transcript` is currently always `""` — ready for future mic integration
- The overlay **never writes to disk** — all screen data is in-memory base64
- The debounce gate also prevents rate-limiting Gemini on the backend side
- The overlay window is invisible to screen recorders (WS_EX_LAYERED flag) — test with `mss` itself to confirm captures look correct
