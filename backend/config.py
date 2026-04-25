import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Model Constants (verified real model IDs as of 2026) ---
# gemini-2.5-flash-lite  = fastest, cheapest, great for structured tasks
# gemini-2.5-flash       = balanced speed/quality
# gemini-2.0-flash       = solid fallback, widely available
DEV_MODEL      = "gemini-2.0-flash"
PROD_MODEL     = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-flash-lite"

# Determine active model from env (defaults to dev model)
ACTIVE_MODEL = os.getenv("LEMIHANDLE_MODEL", DEV_MODEL)

# --- Output Directory ---
# Files saved by the AI agent land here. Created at startup.
USER_HOME  = Path.home()
OUTPUT_DIR = USER_HOME / "Desktop" / "lemihandle_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- API Key Pool ---
API_KEYS_STR = os.getenv("GEMINI_API_KEYS", "")
API_KEYS = [
    k.strip()
    for k in API_KEYS_STR.split(",")
    if k.strip() and k.strip() != "your_api_key_here"
]

if not API_KEYS:
    print("[WARNING] GEMINI_API_KEYS is missing or invalid in .env — add it before running!")
    API_KEYS = ["dummy_key"]
