# Implementation Plan: Part B — The Backend ("Brain")

## Goal
Build the FastAPI microservice that receives multimodal input (screenshot + voice transcript) from the Frontend, orchestrates a Gemini/Gemma model call with **Function Calling** and **Structured Outputs**, executes any triggered OS actions, and returns a strict JSON directive.

> [!IMPORTANT]
> **We are only building Part B.** The Frontend (Part A) is being handled independently by a remote teammate. We communicate exclusively via the JSON contract defined below. Our code must never assume the frontend exists locally.

---

## Environment & Constraints

| Detail | Value |
|---|---|
| **Python** | 3.10.7 (via `py` launcher on Windows) |
| **Pip** | `py -m pip` (direct `pip` / `python` not on PATH) |
| **SDK** | `google-genai` (the modern unified SDK, **not** the legacy `google-generativeai`) |
| **Dev Model** | `gemma-4-31b-it` — 15 RPM, Unlimited TPM, **1,500 RPD** |
| **Prod Model** | `gemini-3-flash` — 5 RPM, 250K TPM, **20 RPD** (use only for final demo) |
| **Fallback Model** | `gemini-3.1-flash-lite` — 15 RPM, 250K TPM, **500 RPD** (middle ground) |
| **Project Dir** | `c:\Users\irsha\Desktop\no_name\backend\` |

> [!WARNING]
> **Gemini 3 Flash has only 20 requests per day.** During development, we will hardcode the model to `gemma-4-31b-it`. We switch to `gemini-3-flash` only when filming the final demo.

---

## Proposed Changes

### Project Structure
```
c:\Users\irsha\Desktop\no_name\
└── backend\
    ├── .env                  # GEMINI_API_KEY=your_key_here
    ├── requirements.txt      # All dependencies
    ├── main.py               # FastAPI server (the core)
    ├── schemas.py            # Pydantic models (request + response)
    ├── tools.py              # Function Calling tool definitions
    ├── config.py             # Model selection, paths, constants
    └── test_ping.py          # Standalone test script
```

---

### Config

#### [NEW] config.py
- Load `GEMINI_API_KEY` from `.env` using `python-dotenv`.
- Define model constants:
  - `DEV_MODEL = "gemma-4-31b-it"`
  - `PROD_MODEL = "gemini-3-flash"`
  - `FALLBACK_MODEL = "gemini-3.1-flash-lite"`
  - `ACTIVE_MODEL` — defaults to `DEV_MODEL`, switchable via env var `LEMIHANDLE_MODEL`.
- Define `OUTPUT_DIR` (default: `~/Desktop/lemihandle_output/`).
- Initialize the `google.genai.Client()` with the API key.

---

### Schemas

#### [NEW] schemas.py
- **`IntentRequest`** (Pydantic model — what we receive):
  ```python
  class IntentRequest(BaseModel):
      trigger_type: str          # "gesture_pinch" or "hotkey"
      screen_b64: str            # Base64-encoded screenshot
      audio_transcript: str      # The user's spoken command
  ```
- **`IntentResponse`** (Pydantic model — what we return, also used as Gemini's `response_schema`):
  ```python
  class IntentResponse(BaseModel):
      status: str                # "success" or "error"
      ui_directive: str          # "display_floating_card", "display_error", etc.
      ai_output: str             # The actual AI-generated content
      function_triggered: str    # "save_to_local_file", "none", etc.
  ```

---

### Tools (Function Calling)

#### [NEW] tools.py
- **`save_output_to_file(content: str, filename: str) -> str`**
  - Writes `content` to `OUTPUT_DIR/filename`.
  - Returns a confirmation string: `"Saved to {path}"`.
  - Has a detailed docstring so Gemini knows when to invoke it.
- **`open_application(app_name: str) -> str`** (stretch goal)
  - Uses `subprocess` to launch an app.
  - Returns confirmation or error.

> [!NOTE]
> We pass these Python functions directly to the SDK as `tools=[save_output_to_file]`. The SDK auto-generates the JSON schema from type hints and docstrings. With **automatic function calling** enabled (default), the SDK will execute the function and feed the result back to the model automatically.

---

### Main Server

#### [NEW] main.py
The core FastAPI application. Here is the exact flow:

1. **Receive** `POST /process_intent` with `IntentRequest` body.
2. **Decode** `screen_b64` from Base64 → raw bytes.
3. **Build the Gemini call:**
   ```python
   from google import genai
   from google.genai import types

   response = client.models.generate_content(
       model=ACTIVE_MODEL,
       contents=[
           types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
           request.audio_transcript,
       ],
       config=types.GenerateContentConfig(
           system_instruction="You are an OS agent. Analyze the screenshot, understand the user's intent from their voice command, and execute. If the user wants to save content, call the save_output_to_file tool. Respond strictly in the required JSON format.",
           tools=[save_output_to_file],
           response_mime_type="application/json",
           response_schema=IntentResponse,
       ),
   )
   ```
4. **Parse** the response into `IntentResponse`.
5. **Return** the JSON to the frontend.
6. **Error handling:** Wrap everything in try/except. On any failure (timeout, API error, malformed response), return:
   ```json
   {"status": "error", "ui_directive": "display_error", "ai_output": "AI Core Offline. Try again.", "function_triggered": "none"}
   ```

Additional endpoints:
- `GET /health` — returns `{"status": "alive", "model": ACTIVE_MODEL}` for quick checks.
- `POST /switch_model` — accepts `{"model": "gemini-3-flash"}` to hot-swap the active model without restarting the server (useful for demo day).

---

### Dependencies

#### [NEW] requirements.txt
```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
google-genai>=1.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pillow>=10.0.0
```

---

### Test Script

#### [NEW] test_ping.py
- Creates a tiny 10x10 red PNG image in memory.
- Base64 encodes it.
- Sends a POST to `http://localhost:8000/process_intent` with:
  ```json
  {
    "trigger_type": "hotkey",
    "screen_b64": "<base64 of the red image>",
    "audio_transcript": "What do you see on my screen?"
  }
  ```
- Prints the full JSON response.
- Validates it matches `IntentResponse` schema.
- Tests the `/health` endpoint.

---

## Execution Order

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Create `backend/` directory structure | `dir backend\` shows all files |
| 2 | Write `config.py`, `schemas.py`, `tools.py` | Files exist, no syntax errors |
| 3 | Write `main.py` | `py -m uvicorn main:app --reload` starts without errors |
| 4 | Create venv & install `requirements.txt` | `py -m pip install -r requirements.txt` succeeds |
| 5 | Set `GEMINI_API_KEY` in `.env` | `GET /health` returns `{"status": "alive"}` |
| 6 | Run `test_ping.py` | Returns valid `IntentResponse` JSON |
| 7 | Test `save_output_to_file` trigger | Say "save this" → file appears in output dir |
| 8 | Switch model to `gemini-3-flash` via `/switch_model` | Verify response still valid (costs 1 of 20 RPD) |
