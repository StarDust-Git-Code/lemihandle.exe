import base64
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types

from config import API_KEYS, ACTIVE_MODEL, PROD_MODEL
from schemas import IntentRequest, IntentResponse
from tools import AVAILABLE_TOOLS

# Basic in-memory history to fulfill the "feed previous context" requirement
CHAT_HISTORY = []

app = FastAPI(title="Lemihandle Spatial Intent Brain")

SYSTEM_INSTRUCTION = """
You are the Brain of a Spatial Intent Engine (an OS overlay). 
You receive a screenshot of what the user is currently looking at, along with their voice transcript/command.
Analyze the screenshot context and the user's intent.
Execute necessary actions. If they ask to save data, extract it from the screen and use the save_output_to_file tool.
Always respond exactly in the required JSON format.
"""

@app.post("/process_intent", response_model=IntentResponse)
def process_intent(request: IntentRequest):
    global CHAT_HISTORY
    try:
        # 1. Decode the base64 image
        try:
            image_bytes = base64.b64decode(request.screen_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image: {e}")

        # 2. Build the current turn parts
        # Using google-genai Part.from_bytes
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        current_text_part = types.Part.from_text(text=request.audio_transcript)
        
        current_parts = [image_part, current_text_part]
        
        # 3. Assemble full contents with history
        contents = []
        for msg in CHAT_HISTORY:
            contents.append(types.Content(
                role=msg["role"], 
                parts=[types.Part.from_text(text=msg["text"])]
            ))
            
        # Add the current user turn
        contents.append(types.Content(
            role="user",
            parts=current_parts
        ))
        
        # 4. Call the model with API key rotation
        print(f"[*] Calling Gemini ({ACTIVE_MODEL}) with transcript: '{request.audio_transcript}'")
        
        gen_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=IntentResponse,
            temperature=0.0, # Low temperature for structured tasks
        )
        
        response = None
        last_exception = None
        
        for key in API_KEYS:
            try:
                local_client = genai.Client(api_key=key)
                response = local_client.models.generate_content(
                    model=ACTIVE_MODEL,
                    contents=contents,
                    config=gen_config
                )
                break # Success!
            except Exception as e:
                err_str = str(e).lower()
                print(f"[!] API Key rotation: caught error with a key: {e}")
                last_exception = e
                # Retry on quota/rate limits, or invalid keys
                if "429" in err_str or "quota" in err_str or "400" in err_str or "invalid" in err_str:
                    continue
                else:
                    raise e # Don't retry on other errors (e.g. malformed request)
                    
        if not response:
            raise Exception(f"All API keys failed or exhausted. Last error: {last_exception}")
        
        # 4. Parse the structured JSON response into our Pydantic model
        if not response.text:
            raise ValueError("Model returned empty response.")
            
        result = IntentResponse.model_validate_json(response.text)
        
        # 5. Save context for next turn
        CHAT_HISTORY.append({"role": "user", "text": request.audio_transcript})
        CHAT_HISTORY.append({"role": "model", "text": response.text})
        
        # Keep history from growing unbounded (limit to last 10 turns = 20 messages)
        if len(CHAT_HISTORY) > 20:
            CHAT_HISTORY = CHAT_HISTORY[-20:]
        
        # 6. Execute Side Effects locally
        try:
            if result.function_triggered == "save_output_to_file":
                from tools import save_output_to_file
                # We use the ai_output as the content to save.
                save_msg = save_output_to_file(content=result.ai_output)
                print(f"[TOOL EXECUTED] {save_msg}")
            elif result.function_triggered == "open_application":
                from tools import open_application
                # Quick regex or string split could extract app name, but for now we just use the output
                app_msg = open_application(app_name="Requested Application")
                print(f"[TOOL EXECUTED] {app_msg}")
        except Exception as tool_e:
            print(f"[ERROR] Failed to execute tool: {tool_e}")
            
        return result

    except Exception as e:
        print(f"[ERROR] {e}")
        # Fallback response to prevent frontend crash
        return IntentResponse(
            status="error",
            ui_directive="display_error",
            ai_output=f"AI Core Offline or Error: {str(e)}",
            function_triggered="none"
        )

@app.get("/health")
def health_check():
    return {"status": "alive", "active_model": ACTIVE_MODEL}

@app.post("/switch_model")
def switch_model(payload: dict):
    global ACTIVE_MODEL
    target = payload.get("model")
    if target:
        ACTIVE_MODEL = target
        return {"status": "success", "active_model": ACTIVE_MODEL}
    raise HTTPException(status_code=400, detail="Missing 'model' in payload")
