# Developer A Walkthrough: Spatial Intent Engine (Frontend)

## Overview

The Frontend (Developer A) acts as the "eyes and ears" of the multimodal AI assistant. It is a lightweight, transparent OS overlay that runs silently in the background, utilizing a webcam and microphone to capture spatial gestures, facial expressions, and voice commands. 

The goal is to allow the user to interact with the AI without ever leaving their active window or workflow.

---

## The Tech Stack

- **UI Framework:** PyQt5 (Transparent borderless `QMainWindow`, custom QPainter graphics)
- **Computer Vision:** MediaPipe Tasks API (`HandLandmarker`, `FaceLandmarker`), OpenCV (`cv2`)
- **Audio Capture:** `sounddevice`, Google SpeechRecognition API
- **Concurrency:** `QThread` (Vision), `threading.Timer` (Debounce), `asyncio`/`requests` (Network)

---

## Core Systems & Features

### 1. The Glassmorphic Overlay
A borderless, full-screen transparent window is rendered over the entire OS.
- **Click-through:** When in the `IDLE` state, Windows API flags (`WS_EX_TRANSPARENT`) are injected so mouse clicks pass right through to the applications below.
- **Non-intrusive UI:** Uses floating "pills" for pending/processing states, and a frosted-glass card for the final AI response.
- **PIP Camera HUD:** A small picture-in-picture widget in the bottom-left corner shows the raw camera feed overlaid with the cyberpunk tracking skeleton (green nodes, blue bones, purple eye dots).

### 2. The Interaction Pipeline
To prevent accidental API calls, triggers require a confirmation.
1. **Trigger:** `Ctrl+Shift+Space` OR open your palm to start recording voice.
2. **Pending:** The UI shows `NOD TWICE TO CONFIRM`.
3. **Confirm:** Nodding your head (or closing your palm) locks in the intent.
4. **Capture:** The engine snaps a base64 screenshot and transcribes the audio.
5. **Network:** Sent asynchronously to the Backend via `POST /process_intent`.

### 3. Face & Hand Tracking Architecture
The `GestureEngine` runs on a dedicated background `QThread` to prevent freezing the PyQt UI. It extracts `w` and `h` from the frame to normalize the 0.0-1.0 landmark coordinates into exact screen pixels.

**Implemented Gestures:**
*   **Head Nod (Confirm):** Tracks the nose tip (`lm[4].y`). Two downward dips below an adaptive baseline within 1.8 seconds.
*   **Head Shake (Dismiss):** Tracks the nose tip (`lm[4].x`). Rapid left-right swings cancel any pending action or active result card.
*   **Jaw PTT (Hands-free Voice):** Uses the `jawOpen` blendshape. Opening the mouth > 0.40 starts recording; closing it < 0.15 stops and submits the query.
*   **Frustration Detection:** Sustained furrowing of both brows (`browDownLeft` + `browDownRight`) for 2.5s. Intended to trigger an "auto-clarify" request to the AI if the user is confused.
*   **Drowsiness Alert:** Calculates Eye Aspect Ratio (EAR). If eyelids are mostly closed for > 25% of a 30-second rolling window, it displays a subtle wellness pill `🌿 You look tired...`
*   **Gaze-Aware Dismiss:** Analyzes head yaw and pitch. If the user looks away from the screen, the 8-second auto-dismiss timer on the result card *pauses*. It resumes only when they look back, ensuring they don't miss the answer.
*   **Panic Quit:** Pressing `Ctrl+Shift+Q` instantly kills the entire background app.

### 4. Audio Engine Safety
Replaced native disk I/O with an in-memory queue. The `sounddevice` stream captures `float32` frames, which are concatenated and safely cast to `int16` PCM so the `SpeechRecognition` library can process the WAV buffer without throwing format errors. Recording and transcribing are fully decoupled.

### 5. System Tray Hardware Toggles
To respect user privacy, a native `QSystemTrayIcon` allows independent disabling of the Camera HUD and the Microphone stream.

---

## Next Steps

The entire frontend is currently running in `MOCK_MODE = True` to prevent crashing while Developer B was building the backend. We are now ready to flip this flag to `False` and perform live integration testing.
