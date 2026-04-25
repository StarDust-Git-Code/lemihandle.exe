"""
tools.py — Executable system tools for the Spatial Intent Engine backend.

These functions are passed to the Gemini SDK as Tools so the model can call
them natively via function calling. Their docstrings and type hints are used
to auto-generate the JSON schema that Gemini sees.
"""

import datetime
import subprocess
import shlex
import sys
from config import OUTPUT_DIR


# ---------------------------------------------------------------------------
# Tool: Save to file
# ---------------------------------------------------------------------------

def save_output_to_file(content: str, filename: str = "") -> str:
    """
    Saves text content or data to a local file on the user's computer.
    Use this tool when the user asks to 'save this', 'export', 'write to file',
    or 'keep a copy'.

    Args:
        content:  The text, code, or data to be saved.
        filename: Optional. A short, descriptive name for the file
                  (e.g., 'summary.txt' or 'data.csv').
                  If not provided, a timestamped name is generated.

    Returns:
        A confirmation string stating where the file was saved.
    """
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intent_output_{timestamp}.txt"

    # Basic sanitization — keep only safe characters
    safe_filename = "".join(
        c for c in filename if c.isalpha() or c.isdigit() or c in (" ", ".", "_", "-")
    ).strip()

    if not safe_filename:
        safe_filename = f"intent_output_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    filepath = OUTPUT_DIR / safe_filename
    filepath.write_text(content, encoding="utf-8")

    print(f"[TOOL] save_output_to_file → {filepath}")
    return f"Successfully saved to {filepath}"


# ---------------------------------------------------------------------------
# Tool: Open application
# ---------------------------------------------------------------------------

def open_application(app_name: str) -> str:
    """
    Opens or launches a named application on the user's Windows computer.
    Use this tool when the user says 'open <app>', 'launch <app>', or
    'start <app>'. Common values: 'notepad', 'calculator', 'chrome',
    'explorer', 'code', 'paint', 'taskmgr', 'cmd', 'powershell'.

    Args:
        app_name: The name or executable of the application to open.
                  Examples: 'notepad', 'calc', 'explorer', 'mspaint'.

    Returns:
        A confirmation string or an error description.
    """
    # Normalize common aliases
    aliases: dict[str, str] = {
        "calculator": "calc",
        "file explorer": "explorer",
        "file manager": "explorer",
        "terminal": "cmd",
        "command prompt": "cmd",
        "vs code": "code",
        "vscode": "code",
        "chrome": "chrome",
        "google chrome": "chrome",
        "notepad++": "notepad++",
        "paint": "mspaint",
    }
    resolved = aliases.get(app_name.lower().strip(), app_name.strip())

    print(f"[TOOL] open_application → '{resolved}'")
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                resolved,
                shell=True,  # shell=True so Windows PATH / aliases work
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            # macOS / Linux fallback (not the primary platform but keep it safe)
            subprocess.Popen(shlex.split(resolved), start_new_session=True)
        return f"Successfully launched '{resolved}'."
    except Exception as exc:
        return f"Failed to open '{resolved}': {exc}"


# ---------------------------------------------------------------------------
# Tool registry — exported and passed to Gemini
# ---------------------------------------------------------------------------

AVAILABLE_TOOLS = [save_output_to_file, open_application]
