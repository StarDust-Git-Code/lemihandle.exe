"""
main.py — FastAPI Spatial Intent Brain (Dev B / Backend)
=========================================================

Route: POST /process_intent
  - Receives trigger_type, screen_b64 (JPEG), audio_transcript
  - Calls Gemini with image + text via API-key rotation
  - Uses native Gemini function calling (AVAILABLE_TOOLS) for side effects
  - Returns structured IntentResponse JSON

Route: GET  /health
Route: POST /switch_model
"""

import base64
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types

from config import API_KEYS, ACTIVE_MODEL, PROD_MODEL
from schemas import IntentRequest, IntentResponse
from tools import AVAILABLE_TOOLS, save_output_to_file, open_application

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Lemihandle Spatial Intent Brain")

SYSTEM_INSTRUCTION = """\
You are the Brain of a Spatial Intent Engine — an invisible AI OS overlay.

You receive:
  1. A screenshot of what the user is currently looking at.
  2. Their spoken voice command (audio_transcript).

Your job:
  • Analyse the screen context and the user's intent.
  • If the user asks to save / export / write data, call save_output_to_file.
  • If the user asks to open / launch an application, call open_application.
  • Always reply in the required structured JSON format.

Be concise, specific, and actionable. Your ai_output will be displayed as a
floating card over the user's screen, so keep it readable — use short
paragraphs or bullet points where helpful.
"""

# In-memory conversation history.
# Stores {"role": str, "text": str, "has_image": bool} per turn.
# We only keep the last 10 user+model pairs (20 entries) to bound memory.
CHAT_HISTORY: list[dict] = []

# Last screenshot b64 string — stored so we can include it in history context
_last_screen_b64: str = ""


# ---------------------------------------------------------------------------
# Helper — build contents list with history
# ---------------------------------------------------------------------------

def _build_contents(image_bytes: bytes, audio_transcript: str) -> list[types.Content]:
    """
    Assemble the full multi-turn contents list:
      [history turns] + [current user turn with image + text]
    """
    contents: list[types.Content] = []

    # Replay history as text-only (images from past turns are dropped to
    # save tokens; the current screenshot provides the fresh visual context)
    for msg in CHAT_HISTORY:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["text"])],
            )
        )

    # Current turn: image + voice transcript
    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
    text_part  = types.Part.from_text(text=audio_transcript or "(no spoken command)")
    contents.append(
        types.Content(role="user", parts=[image_part, text_part])
    )
    return contents


# ---------------------------------------------------------------------------
# Helper — call Gemini with key rotation
# ---------------------------------------------------------------------------

def _call_gemini(
    contents: list[types.Content],
    gen_config: types.GenerateContentConfig,
) -> types.GenerateContentResponse:
    """Try each API key in order; break on first success; raise on all failures."""
    last_exc: Exception | None = None
    for key in API_KEYS:
        try:
            client   = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=ACTIVE_MODEL,
                contents=contents,
                config=gen_config,
            )
            return response
        except Exception as exc:
            err = str(exc).lower()
            print(f"[API] Key rotation — error: {exc}")
            last_exc = exc
            # Retry on quota / rate-limit / auth errors; bail on others
            if any(code in err for code in ("429", "quota", "401", "403", "invalid")):
                continue
            raise exc  # hard failure — propagate immediately
    raise RuntimeError(
        f"All {len(API_KEYS)} API key(s) failed. Last error: {last_exc}"
    )


# ---------------------------------------------------------------------------
# POST /process_intent
# ---------------------------------------------------------------------------

@app.post("/process_intent", response_model=IntentResponse)
def process_intent(request: IntentRequest) -> IntentResponse:
    global CHAT_HISTORY, _last_screen_b64, ACTIVE_MODEL

    try:
        # 1. Decode image --------------------------------------------------------
        try:
            image_bytes = base64.b64decode(request.screen_b64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}")

        _last_screen_b64 = request.screen_b64  # stash for debugging

        # 2. Build contents ------------------------------------------------------
        contents = _build_contents(image_bytes, request.audio_transcript)

        # 3. Gemini config — structured output + native function calling ---------
        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=IntentResponse,
            temperature=0.0,
            tools=AVAILABLE_TOOLS,          # ← real function calling enabled
        )

        print(
            f"[*] Calling {ACTIVE_MODEL} | "
            f"transcript='{request.audio_transcript}' | "
            f"history_turns={len(CHAT_HISTORY) // 2}"
        )

        # 4. Call model ----------------------------------------------------------
        response = _call_gemini(contents, gen_config)

        if not response.text:
            raise ValueError("Model returned an empty response.")

        # 5. Handle native function calls from Gemini ----------------------------
        #    When Gemini natively calls a tool it returns function_call parts.
        #    We execute them here before parsing the final JSON reply.
        tool_name_executed = "none"
        if response.candidates:
            for candidate in response.candidates:
                if not candidate.content:
                    continue
                for part in candidate.content.parts:
                    if not part.function_call:
                        continue
                    fc   = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    print(f"[TOOL CALL] Gemini requested: {fc.name}({args})")

                    if fc.name == "save_output_to_file":
                        result_msg = save_output_to_file(**args)
                        tool_name_executed = "save_output_to_file"
                        print(f"[TOOL RESULT] {result_msg}")

                    elif fc.name == "open_application":
                        result_msg = open_application(**args)
                        tool_name_executed = "open_application"
                        print(f"[TOOL RESULT] {result_msg}")

        # 6. Parse structured JSON response --------------------------------------
        result = IntentResponse.model_validate_json(response.text)

        # If Gemini executed a real function call, override the schema field
        if tool_name_executed != "none":
            result.function_triggered = tool_name_executed

        # Fallback: honour schema-reported function_triggered for save
        # (in case model chose to report via schema rather than function_call)
        elif result.function_triggered == "save_output_to_file":
            msg = save_output_to_file(content=result.ai_output)
            print(f"[TOOL FALLBACK] {msg}")

        elif result.function_triggered == "open_application":
            # Extract app name from ai_output as best-effort fallback
            import re
            m = re.search(r"open(?:ing|ed)?\s+['\"]?([A-Za-z0-9 +]+)['\"]?", result.ai_output, re.I)
            app_name = m.group(1).strip() if m else "notepad"
            msg = open_application(app_name=app_name)
            print(f"[TOOL FALLBACK] {msg}")

        # 7. Update history ------------------------------------------------------
        CHAT_HISTORY.append({"role": "user",  "text": request.audio_transcript})
        CHAT_HISTORY.append({"role": "model", "text": response.text})
        # Cap at 20 entries (10 turn pairs)
        if len(CHAT_HISTORY) > 20:
            CHAT_HISTORY = CHAT_HISTORY[-20:]

        return result

    except HTTPException:
        raise  # let FastAPI handle 4xx as-is

    except Exception as exc:
        print(f"[ERROR] {exc}")
        return IntentResponse(
            status="error",
            ui_directive="display_error",
            ai_output=f"AI Core Error: {str(exc)}",
            function_triggered="none",
        )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> dict:
    return {
        "status": "alive",
        "active_model": ACTIVE_MODEL,
        "api_key_count": len(API_KEYS),
    }


# ---------------------------------------------------------------------------
# POST /switch_model
# ---------------------------------------------------------------------------

@app.post("/switch_model")
def switch_model(payload: dict) -> dict:
    global ACTIVE_MODEL
    target = payload.get("model", "").strip()
    if target:
        ACTIVE_MODEL = target
        print(f"[Config] Model switched to: {ACTIVE_MODEL}")
        return {"status": "success", "active_model": ACTIVE_MODEL}
    raise HTTPException(status_code=400, detail="Missing 'model' in payload")
