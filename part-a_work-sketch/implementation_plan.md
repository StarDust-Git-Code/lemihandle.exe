# Dev A — Extended Independent Roadmap (Before Phase 3 Integration)

Because Developer A and Developer B communicate strictly via an immutable JSON contract (`http://localhost:8000/process_intent`), **Developer A can build and test almost 100% of the frontend in complete isolation** using `MOCK_MODE`.

Here is the plan for what Developer A can build right now, without waiting for Developer B.

---

## 1. Additional Hand Gestures (The Spatial Interface)

Right now, we only have a "Pinch" trigger. We can expand `gesture_engine.py` to detect multiple distinct topological states of the hand. 

### Proposed Gestures to Add:
1. **The "Swipe" (Dismiss)**: Rapid horizontal movement of an open palm. 
   - *Local Action*: Instantly dismisses the floating AI result card or cancels a pending request.
2. **The "Open Palm" (Pause/Listen)**: Holding a flat hand up to the camera.
   - *Local Action*: Acts as a "push-to-talk" mechanism for audio. While the palm is up, the microphone records. When the palm drops, it triggers the payload.
3. **The "Point" (Index finger up, others closed)**: 
   - *Local Action*: Could be used in the future to map your finger to the mouse cursor to draw bounding boxes on the screen before triggering.
4. **Thumbs Up / Thumbs Down**:
   - *Local Action*: If an AI result is currently on screen, doing this gesture instantly dismisses the card and logs a local feedback metric.

## User Review Required
> [!IMPORTANT]
> **Which of these gestures would you like me to implement next?** The "Open Palm" to trigger audio recording is highly recommended to fulfill the audio requirement of the contract.

---

## 2. Audio Capture & Transcription (Filling the JSON Contract)

The immutable contract requires: `"audio_transcript": "<string>"`. 
Currently, Dev A hardcodes this as `""`. Because Dev B expects a *string* (not raw audio bytes), Dev A is responsible for local Speech-to-Text.

**Independent Implementation Plan:**
- Add `SpeechRecognition` and `PyAudio` (or `sounddevice`) to `requirements.txt`.
- Create `audio_engine.py`.
- **Workflow**: 
  1. Trigger fired (e.g. Open Palm or hotkey held down).
  2. Overlay transitions to a `LISTENING` state (a red pulsing microphone icon).
  3. Audio is recorded until silence is detected or the gesture ends.
  4. Audio is transcribed locally (using a fast offline model like Vosk, or Google's free online API for prototyping).
  5. The transcribed text string is injected into the JSON payload alongside the screen base64.

---

## 3. UI Directive Routing (Future-Proofing for Dev B)

Dev B's response contract contains: `"ui_directive": "display_floating_card"`.
Right now, Dev A assumes everything is a floating card. Dev A can build out a robust "Directive Router" in `overlay.py` to handle different types of UI requests Dev B might throw at it in the future:

- `"display_floating_card"`: The current frosted glass card.
- `"display_notification"`: A small, non-intrusive toast notification in the bottom right corner (e.g. for background tasks).
- `"execute_action_badge"`: If Dev B's JSON includes `"function_triggered": "save_output_to_file"`, Dev A should render a special glowing icon on the UI that says "Action Executed: Saved to File".

Dev A can test all of these independently by simply changing the `mock_response.json` file and verifying the UI updates correctly.

---

## 4. System Tray Integration (Quality of Life)

Since the app has no standard "window", the user currently has no way to close it other than killing the terminal process. 
Dev A can implement a system tray icon (using `pystray`) in the Windows taskbar.

**Tray Menu Options:**
- **Status:** Shows "Mock Mode Active" or "Live Mode Active".
- **Toggle Mode:** Instantly flips `MOCK_MODE` on or off without restarting.
- **Camera Selection:** Dropdown to select which webcam to use.
- **Quit:** Gracefully shuts down the Qt Event loop, MediaPipe thread, and keyboard hooks.

---

## Open Questions

> [!CAUTION]
> **Awaiting your approval to proceed.** Developer A is ready to execute all of the above without any interference from Developer B. 
> 
> Please let me know:
> 1. Should we prioritize the **Audio Transcription** pipeline next so the JSON contract is 100% fulfilled?
> 2. Or should we prioritize **System Tray / QoL** so the app feels like a real background OS daemon?
> 3. Or should we add the **Swipe & Open Palm** gestures to the MediaPipe engine?
