# My Work: Part B (The Backend / "Brain")

This document outlines the specific goals and responsibilities for our portion of the Lemihandle project.

## Goal
To build a local FastAPI microservice that acts as the "Brain" of the Spatial Intent Engine. It will receive screen context and voice intent from the Frontend (handled by our remote teammate), process it using Gemini/Gemma models, execute necessary OS-level actions locally, and return a structured JSON directive back to the Frontend.

## Tech Stack
*   **Language:** Python
*   **Framework:** `FastAPI`, `uvicorn`
*   **Data Validation:** `Pydantic`
*   **AI SDK:** `google-generativeai`

## Target AI Models
*   **Development/Testing:** `Gemma 4` (1.5K Requests Per Day) to avoid rate limits.
*   **Production/Final Demo:** `Gemini 3 Flash` (Extremely strict 20 Requests Per Day limit).

## Core Responsibilities
1.  **The Server:** Run a local `FastAPI` instance exposing `http://localhost:8000/process_intent`.
2.  **Decoding:** Parse the incoming JSON payload and decode the Base64 screen image into bytes.
3.  **AI Orchestration:** Send the image bytes and text intent to the active AI model.
4.  **Strict Enforcement:** Use **Structured Outputs** (via `response_schema`) to force the AI to return data in the exact JSON format required by the Frontend.
5.  **Agentic Execution:** Use **Function Calling** (Tools) to define Python functions like `save_output_to_file()`. If the AI determines a file needs saving, the backend executes this local Python function *before* returning the final JSON to the Frontend.

## The Immutable Data Contract
We must adhere to this exact JSON structure for communication with Part A.

**What We Receive (HTTP POST from Frontend):**
```json
{
  "trigger_type": "gesture_pinch", 
  "screen_b64": "iVBORw0KGgo...", 
  "audio_transcript": "Summarize this data table and save it." 
}
```

**What We Reply (HTTP 200 OK to Frontend):**
```json
{
  "status": "success",
  "ui_directive": "display_floating_card",
  "ai_output": "Table summarized. Saved to local file.",
  "function_triggered": "save_to_local_file" 
}
```

## Immediate Execution Plan (Phase 1)
1.  Initialize a Python virtual environment.
2.  Install backend dependencies (`fastapi`, `uvicorn`, `google-generativeai`, `pydantic`).
3.  Write `backend/main.py`. Set up the `/process_intent` route.
4.  Integrate the `google-generativeai` SDK configured for `Gemma 4`.
5.  Implement the Pydantic schemas and the `save_output_to_file` function tool.
6.  Write a `test_ping.py` script to verify the API independently.
