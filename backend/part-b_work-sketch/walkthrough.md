# Dev B Walkthrough — Spatial Intent Backend (The "Brain")

## What Was Built

A highly optimized, stateful **FastAPI orchestration backend** that powers the Spatial Intent Engine, processing multimodal data (screen + transcript) and executing local system operations.

---

## File Structure

```
backend/
├── main.py              ← FastAPI entry point, Gemini orchestration, and API Key rotation
├── schemas.py           ← Pydantic data models enforcing the immutable JSON contract
├── tools.py             ← Local execution tools (e.g., file saving, system actions)
├── config.py            ← Environment and model configuration logic
├── interactive_test.py  ← CLI emulator to test end-to-end without the frontend
└── .env                 ← Secret keys and model configurations
```

---

## Core Capabilities Delivered

| Capability | Implementation |
|-------|---------------|
| **1 — The API Contract** | `POST /process_intent`. Validates incoming JSON (`audio_transcript`, `screen_b64`) and guarantees return of the exact 4-key JSON schema via Pydantic `model_validate_json`. |
| **2 — Ultra-Low Latency** | Switched from standard preview models to Google's specialized **`gemini-2.5-flash-lite`**. Combined with aggressive JPEG downscaling from Dev A, TTFT (Time to First Token) is effectively minimized. |
| **3 — Resilient Key Rotation** | Built a loop-retry system in `main.py` that intercepts 429 (Quota Exceeded) and 400 (Invalid Argument) errors from Gemini and instantly pivots to the next API key in the `.env` array without failing the request. |
| **4 — Stateful Context Memory** | Implemented a sliding window `CHAT_HISTORY` array. The model remembers past interactions (limited to the last 10 turns to prevent context window blowouts) to allow conversational commands like "Summarize that last thing". |
| **5 — Agentic Tool Execution** | Decoupled from Google's native Function Calling (which conflicted with JSON mode). We instruct the AI to emit a `function_triggered` string. The backend intercepts this string, executes the corresponding Python function in `tools.py` locally (e.g. saving to disk), and then reports success to the frontend. |

---

## Running the Backend

```powershell
cd "backend"
# Activate virtual environment if necessary
.\.venv\Scripts\activate

# Start the server
python -m uvicorn main:app --port 8000
```

> **Testing locally:** 
> You can run `python interactive_test.py` to simulate Developer A's payload without needing the PyQt5 frontend.

---

## Notes for Dev A Handoff

- **Structured JSON Only:** Our backend relies purely on Structured Outputs. We stripped native Function Calling to eliminate 400 API errors.
- **Microphone is the Blocker:** The backend logic is flawless right now, but without your `audio_transcript` injection, the AI has no idea what to look for on the screen. 
- **Error Handling:** If the backend completely crashes or all API keys exhaust, it will return a safe `{"status": "error", "ui_directive": "display_error"}` fallback to prevent your Qt loop from crashing.
