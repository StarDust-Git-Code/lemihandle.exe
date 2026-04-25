# constants.py — Shared configuration for Spatial Intent Engine (Dev A)
# =========================================================================
# Toggle MOCK_MODE = False to connect to the live FastAPI backend (Dev B).
# All other constants are environment-agnostic.

# ── Phase toggles ─────────────────────────────────────────────────────────
MOCK_MODE: bool = True          # Phase 1: True → read mock_response.json
                                # Phase 3: False → POST to BACKEND_URL

# ── Network ───────────────────────────────────────────────────────────────
BACKEND_URL: str = "http://localhost:8000/process_intent"
REQUEST_TIMEOUT_S: int = 30     # seconds before we surface a timeout error

# ── Gesture engine ────────────────────────────────────────────────────────
PINCH_THRESHOLD_PX: int = 20   # Euclidean distance (px) for pinch detection
CAMERA_INDEX: int = 0           # Default webcam index

# ── Keyboard trigger ──────────────────────────────────────────────────────
HOTKEY: str = "ctrl+shift+space"
QUIT_HOTKEY: str = "ctrl+shift+q"

# ── Debounce (Phase 2) ────────────────────────────────────────────────────
DEBOUNCE_SECONDS: float = 3.0   # Cooldown between consecutive triggers

# ── UI timing ─────────────────────────────────────────────────────────────
RESULT_DISPLAY_MS: int = 8_000  # Auto-dismiss result card after 8 seconds
FADE_DURATION_MS: int = 350     # Fade-in / fade-out animation duration

# ── Visual theme ──────────────────────────────────────────────────────────
NEON_COLOR      = (0, 240, 200)          # (R,G,B) teal neon accent
BG_COLOR        = (10, 10, 25, 210)      # (R,G,B,A) deep-space card background
SPINNER_FRAMES  = ["◐", "◓", "◑", "◒"]  # CLI-style spinner characters
FONT_FAMILY     = "Segoe UI"
FONT_SIZE_BODY  = 14
FONT_SIZE_TITLE = 11
