from pydantic import BaseModel, Field

# The immutable contract: What we receive from Part A (Frontend)
class IntentRequest(BaseModel):
    trigger_type: str = Field(description="The trigger type, e.g., 'gesture_pinch' or 'hotkey'.")
    screen_b64: str = Field(description="Base64-encoded screenshot image.")
    audio_transcript: str = Field(description="The spoken command or text intent from the user.")

# The immutable contract: What we send back to Part A (Frontend)
# This is also passed to Gemini as the `response_schema`
class IntentResponse(BaseModel):
    status: str = Field(description="'success' or 'error'")
    ui_directive: str = Field(description="Instruction for the UI, e.g., 'display_floating_card'")
    ai_output: str = Field(description="The actual AI-generated content or answer.")
    function_triggered: str = Field(description="Name of the local function executed, e.g., 'save_output_to_file' or 'none'.")
