import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

# --- Model Constants ---
DEV_MODEL = "gemma-4-31b-it"
PROD_MODEL = "gemini-3-flash"
FALLBACK_MODEL = "gemini-3.1-flash-lite"

# Determine active model (default to dev)
ACTIVE_MODEL = os.getenv("LEMIHANDLE_MODEL", DEV_MODEL)

# --- Directories ---
# Default to Desktop/lemihandle_output
USER_HOME = Path.home()
OUTPUT_DIR = USER_HOME / "Desktop" / "lemihandle_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- GenAI Clients ---
API_KEYS_STR = os.getenv("GEMINI_API_KEYS", "")
API_KEYS = [k.strip() for k in API_KEYS_STR.split(",") if k.strip() and k.strip() != "your_api_key_here"]

if not API_KEYS:
    print("WARNING: GEMINI_API_KEYS is missing or invalid in .env")
    API_KEYS = ["dummy_key"]
