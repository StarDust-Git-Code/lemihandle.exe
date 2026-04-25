import os
import datetime
from config import OUTPUT_DIR

# -----------------------------------------------------------------------------
# Function Calling Tools
# These functions are passed directly to the Gemini SDK. The SDK uses their
# docstrings and type hints to automatically generate the JSON schema.
# -----------------------------------------------------------------------------

def save_output_to_file(content: str, filename: str = None) -> str:
    """
    Saves text content or data to a local file on the user's computer. 
    Use this tool when the user asks to "save this", "export", or "keep a copy".
    
    Args:
        content: The text, code, or data to be saved.
        filename: Optional. A short, descriptive name for the file (e.g., 'summary.txt' or 'data.csv'). 
                  If not provided, a timestamped name will be generated.
    
    Returns:
        A confirmation string stating where the file was saved.
    """
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intent_output_{timestamp}.txt"
        
    # Ensure it's a safe filename (basic sanitization)
    safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
    
    filepath = OUTPUT_DIR / safe_filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return f"Successfully saved to {filepath}"

def open_application(app_name: str) -> str:
    """
    Simulates opening an application on the user's OS.
    Use this if the user says "open notepad" or "launch browser".
    
    Args:
        app_name: The name of the application to open.
    """
    # Note: A real implementation would use subprocess.Popen
    # For now, we simulate success for the hackathon.
    print(f"[TOOL EXECUTION] Simulated opening application: {app_name}")
    return f"Simulated opening {app_name}"

# List of all available tools to pass to the Gemini config
AVAILABLE_TOOLS = [save_output_to_file, open_application]
