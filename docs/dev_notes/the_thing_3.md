Print this out. Put it on your second monitor. Do not deviate from this document. 

Here is the finalized, rubric-optimized, zero-bullshit blueprint for your GEMINI.EXE hackathon submission. *Idhu dhaan plan.* (This is the plan).

---

# THE ZERO-HOUR BLUEPRINT: SPATIAL INTENT ENGINE

## 1. The Core Pitch (For the Judges)
**Problem:** Context switching breaks workflows. Getting AI to understand what you are looking at requires manual screenshots, copying, and typing.
**Solution:** A multimodal, transparent OS overlay. Point at your screen, pinch your fingers (or use a hotkey), and speak. The Gemini agent sees your screen, hears your command, and executes the OS-level task instantly without you leaving your app.

## 2. The Immutable Contract (The JSON Bridge)
Dev A and Dev B will communicate entirely via a local `FastAPI` server running on `http://localhost:8000/process_intent`. 

**Dev A sends (HTTP POST):**
```json
{
  "trigger_type": "gesture_pinch", 
  "screen_b64": "iVBORw0KGgo...", 
  "audio_transcript": "Summarize this data table and save it." 
}
```

**Dev B replies (HTTP Response):**
```json
{
  "status": "success",
  "ui_directive": "display_floating_card",
  "ai_output": "Table summarized. Saved to local file.",
  "function_triggered": "save_to_local_file" 
}
```
*Rule: Do not change this schema without a verbal agreement.*

---

## 3. Developer A: The Front-End (The "Skin")
**Tech:** `Python`, `PyQt5` (or `customtkinter`), `MediaPipe`, `mss`, `keyboard`, `requests`.

**Your Pipeline:**
1. **The Transparent Canvas:** Launch a borderless, transparent, full-screen UI that ignores mouse clicks (`WS_EX_TRANSPARENT`). Add a hidden "Processing..." UI element.
2. **The Dual-Trigger:** * **Primary:** Run MediaPipe. Track thumb to index finger distance. Distance < 20px = Trigger.
   * **Safety Net:** Hook `keyboard.add_hotkey('ctrl+shift+space', trigger_func)`.
3. **The Capture:** On Trigger, instantly freeze the loop. Use `mss` to screenshot the screen. Use a fast library to capture 3 seconds of audio (or just use a hardcoded text string for testing to save time). 
4. **The Send:** Convert the image to Base64. Show the "Processing..." UI. Send the JSON to Dev B via `requests.post`. 
5. **The Render:** Receive Dev B's JSON. Hide the "Processing..." UI. Render `ai_output` on the transparent canvas.

---

## 4. Developer B: The Back-End (The "Brain")
**Tech:** `FastAPI`, `google-generativeai` (Gemini 3 Flash (or gemma 4)), `Pydantic`.

**Your Pipeline:**
1. **The Microservice:** Write a `FastAPI` app. Expose `POST /process_intent`. Parse Dev A's JSON. Decode the Base64 image into bytes.
2. **The Gemini Call:** Pass the image bytes and text/audio transcript to `gemini-1.5-flash`.
3. **The Rubric Hack (Structured Output):** Force Gemini's output into the JSON schema using `response_schema`. 
   * *System Prompt:* "You are an OS agent. Look at the screenshot, read the user's intent, and execute. Reply strictly in JSON."
4. **The Rubric Hack (Function Calling):** Define a Python function `save_output_to_file(content)`. Pass this as a Tool to Gemini. If the user asks to save something, Gemini must trigger this tool. Your FastAPI script executes the Python save function before replying to Dev A.
5. **The Fallback:** If Gemini times out, catch the error and return `{"status": "error", "ai_output": "AI Core Offline"}` so Dev A's UI doesn't crash.

---

## 5. The Brutal Timeline (Hours 4 to 12)

* **Hours 4-7 (Total Isolation):** * Dev A builds the UI, gestures, and hotkeys. Tests with a dummy JSON response.
  * Dev B builds the FastAPI server and Gemini integration. Tests by sending manual Postman requests.
* **Hours 7-10 (The Polish):**
  * Dev A makes the UI look futuristic and ensures the `mss` screenshot is taking less than 0.5 seconds.
  * Dev B fine-tunes the Gemini System Prompt to ensure it accurately reads spreadsheets and code from the screenshots.
* **Hour 11 (The Integration - DROP DEAD DEADLINE):**
  * Both developers stop building features. 
  * Dev A changes the endpoint to `localhost`. You test the live pipeline. You spend this hour fixing CORS errors, base64 decoding issues, and JSON mismatches.
* **Hour 12 (The Rehearsal):**
  * Open a messy spreadsheet. Trigger the hotkey. Say "Extract this." Verify the output works. Record a backup video immediately in case the live demo fails.

---

### The Socratic Challenge

This is your final checkpoint before execution. You have the blueprint. You know the risks. 

**Are you going to waste the next 30 minutes looking for the "perfect" UI library, or are you going to open your terminals right now and start writing the FastAPI bridge and the PyQt5 canvas?** Make your choice. Go.