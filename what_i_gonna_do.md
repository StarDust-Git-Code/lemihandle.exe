# What We Are Going To Do: Project Lemihandle

This document is the absolute, pinpoint, structured execution plan for building **lemihandle.exe** (The Spatial Intent Engine) for the GEMINI.EXE hackathon.

---

## 1. The Core Objective
We are building a **frictionless, multimodal OS overlay**. 
Instead of switching tabs to use an AI, the user stays in their active workflow. By performing a physical gesture (pinching fingers) and speaking, the AI instantly sees the user's screen, understands the intent, and executes the OS-level task (e.g., summarizing data, saving files) via a transparent UI layer.

## 2. The Microservice Architecture
The system is cleanly split into two local components communicating via HTTP.

### Part A: The Frontend (The "Skin") - [ASSIGNED TO: Remote Teammate (20km away)]
*   **Role:** Handles user input, screen capture, and UI rendering.
*   **Tech Stack:** Python, `PyQt5`, `MediaPipe`, `mss`, `keyboard`, `requests`.
*   **Core Responsibilities:**
    1.  **Transparent Canvas:** Run a borderless, full-screen, click-through UI using `PyQt5` (`WS_EX_TRANSPARENT`).
    2.  **Dual-Trigger System:** 
        *   **Primary:** Run `MediaPipe` locally. Continuously track hand landmarks. Trigger when the distance between thumb and index finger is < 20px (Pinch-and-Hold).
        *   **Safety Net:** Listen for a global hotkey (`ctrl+shift+space`) via the `keyboard` library.
    3.  **Capture & Send:** On trigger, freeze the tracking loop. Use `mss` to capture the screen instantly (< 0.5s). Base64 encode the image, attach the intent transcript, and `POST` it to the backend. Show a "Processing..." indicator.
    4.  **Render Response:** Receive the backend's JSON response, clear the "Processing..." state, and render the `ai_output` floating on the user's screen.

### Part B: The Backend (The "Brain") - [ASSIGNED TO: Us (User + Antigravity AI)]
*   **Role:** Handles AI orchestration and local system execution.
*   **Tech Stack:** Python, `FastAPI`, `Pydantic`, `google-generativeai`.
*   **Target AI Models:** 

    *   **Development/Testing:** `Gemma 4` (1.5K Requests Per Day) to avoid rate limits.
    *   **Production/Final Demo:** `Gemini 3 Flash` (Extremely strict 20 Requests Per Day limit).
*   **Core Responsibilities:**
    1.  **The Server:** Run a local `FastAPI` instance exposing `http://localhost:8000/process_intent`.
    2.  **Decoding:** Parse the incoming JSON payload and decode the Base64 screen image into bytes.
    3.  **AI Orchestration:** Send the image bytes and text intent to the active AI model.
    4.  **Strict Enforcement:** Use **Structured Outputs** (via `response_schema`) to force the AI to return data in the exact JSON format required by the Frontend.
    5.  **Agentic Execution:** Use **Function Calling** (Tools) to define Python functions like `save_output_to_file()`. If the AI determines a file needs saving, the backend executes this local Python function *before* returning the final JSON to the Frontend.

---

## 3. The Immutable Data Contract
Dev A and Dev B will communicate *strictly* using the following JSON schema. No deviations allowed without verbal agreement.

**Frontend sends to Backend (HTTP POST):**
```json
{
  "trigger_type": "gesture_pinch", 
  "screen_b64": "iVBORw0KGgo...", 
  "audio_transcript": "Summarize this data table and save it." 
}
```

**Backend replies to Frontend (HTTP 200 OK):**
```json
{
  "status": "success",
  "ui_directive": "display_floating_card",
  "ai_output": "Table summarized. Saved to local file.",
  "function_triggered": "save_to_local_file" 
}
```

---

## 4. Step-by-Step Execution Phases

### Phase 1: Backend Foundation (The Safe Zone)
1.  Initialize a Python virtual environment.
2.  Install backend dependencies (`fastapi`, `uvicorn`, `google-generativeai`, `pydantic`).
3.  Write `backend/main.py`. Set up the `/process_intent` route.
4.  Integrate the `google-generativeai` SDK. Configure it to use `Gemma 4` initially to preserve the `Gemini 3 Flash` quota.
5.  Implement the Pydantic schemas and the `save_output_to_file` function tool.
6.  **Verification:** Write a `test_ping.py` script that POSTs a dummy base64 image and text to `localhost:8000` to guarantee the JSON schema holds up.

### Phase 2: Frontend Foundation (The Danger Zone)
1.  Install frontend dependencies (`PyQt5`, `mediapipe`, `mss`, `keyboard`, `opencv-python`).
2.  Write `frontend/main.py`.
3.  Create the transparent `PyQt5` window. If the OS fights the click-through property (`WS_EX_TRANSPARENT`), we will fallback to a standard semi-transparent window immediately to save time.
4.  Implement the `MediaPipe` webcam loop and the `mss` screenshot logic.
5.  Link the trigger to the `requests.post()` call.

### Phase 3: Integration & Hardening (The Drop-Dead Deadline)
1.  Run both components simultaneously.
2.  Resolve inevitable Base64 decoding errors, CORS issues (if any), and UI threading blocks (ensuring the PyQt5 UI doesn't freeze while waiting for the FastAPI response).
3.  Add fallback error handling: If the API times out, the backend must return a safe `{"status": "error"}` JSON so the frontend doesn't crash.

### Phase 4: Rehearsal
1.  Switch the backend model from `Gemma 4` to `Gemini 3 Flash`.
2.  Open a complex spreadsheet.
3.  Perform the pinch gesture.
4.  Issue the command: "Extract this."
5.  Record the execution for the hackathon submission.
