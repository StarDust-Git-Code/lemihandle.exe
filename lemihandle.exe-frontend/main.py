"""
main.py — Entry point for the Spatial Intent Engine (Frontend)
==============================================================
Wires together:
  • SIEOverlay      (PyQt5 transparent OS overlay)
  • GestureEngine   (MediaPipe QThread — camera path)
  • keyboard hook   (hotkey path)
  • AudioEngine     (push-to-talk recording + transcription)
  • AppController   (QObject owning the confirmation timer)
  • System Tray     (QSystemTrayIcon — camera / mic toggles)
  • network.send_async (non-blocking POST to FastAPI backend)

Trigger workflow
----------------
1. A gesture or hotkey fires _on_trigger(trigger_type).
2. The system enters PENDING state: overlay shows "NOD TWICE TO CONFIRM"
   and a 3-second countdown starts.
3a. User nods twice ➜ _on_head_nodded() → _on_double_blink() → _execute_action():
    screen capture (off-thread) → show PROCESSING → POST to backend.
3b. Timer expires without a nod ➜ action silently aborts, UI resets.
4. Backend responds ➜ overlay shows RESULT card, auto-dismisses after 8 s.

Audio (palm / jaw) workflow
----------------------------
1. Open-palm OR mouth-open ➜ start_recording() + show LISTENING.
2. Palm → fist OR mouth closes ➜ stop_recording() + transcribe (background)
   then call _on_trigger("gesture_palm", transcript).
3. Palm → relaxed (not fist) ➜ stop_recording() + discard, dismiss UI.

Dismiss (fist) workflow
-----------------------
A fist while NOT in audio-listening state cancels any pending action and
resets the UI immediately.
"""

import sys
import threading
from typing import Optional

import keyboard
from PyQt5.QtCore import (
    QMetaObject, QObject, Qt, Q_ARG, QTimer, pyqtSlot
)
from PyQt5.QtGui import QIcon, QImage
from PyQt5.QtWidgets import (
    QAction, QApplication, QMenu, QStyle, QSystemTrayIcon
)

from audio_engine import AudioEngine
from capture import capture_screen_b64
from constants import DEBOUNCE_SECONDS, HOTKEY, QUIT_HOTKEY, MOCK_MODE
from gesture_engine import GestureEngine
from network import send_async
from overlay import SIEOverlay

# ── Globals ────────────────────────────────────────────────────────────────
_overlay:    Optional[SIEOverlay]      = None
_gesture:    Optional[GestureEngine]   = None
_audio:      Optional[AudioEngine]     = None
_controller: Optional["AppController"] = None
_tray:       Optional[QSystemTrayIcon] = None

_mic_enabled:    bool          = True   # toggled from system tray
_pending_action: Optional[dict] = None  # set while awaiting nod confirmation
_debounce_lock   = threading.Event()    # set = engine is cooling down


# ── App controller (owns the confirmation timer — lives on Qt main thread) ──
class AppController(QObject):
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        # 3 seconds — enough time to read the prompt and nod twice deliberately
        self._timer.setInterval(3000)
        self._timer.timeout.connect(_on_pending_timeout)

    @pyqtSlot()
    def start_timer(self) -> None:
        self._timer.start()

    @pyqtSlot()
    def stop_timer(self) -> None:
        self._timer.stop()


# ── Debounce helpers ───────────────────────────────────────────────────────
def _lock_debounce() -> None:
    _debounce_lock.set()
    # Pause the gesture engine so no spurious signals fire during cooldown
    if _gesture:
        _gesture.pause()


def _release_debounce() -> None:
    _debounce_lock.clear()
    if _gesture:
        _gesture.resume()
    print("[Debounce] Re-enabled.")


def _schedule_release() -> None:
    t = threading.Timer(DEBOUNCE_SECONDS, _release_debounce)
    t.daemon = True
    t.start()


# ── Pending-action timeout (runs on Qt main thread via QTimer) ─────────────
@pyqtSlot()
def _on_pending_timeout() -> None:
    global _pending_action
    if _pending_action is None:
        return
    print("[Trigger] Nod timeout — action cancelled.")
    _pending_action = None
    _release_debounce()
    if _overlay:
        _overlay._dismiss()


# ── Trigger entry point ────────────────────────────────────────────────────
def _on_trigger(trigger_type: str, audio_transcript: str = "") -> None:
    """
    Called from gesture callbacks or the keyboard hook (background threads).
    Transitions the system into PENDING state — waits for a head nod before
    actually executing.
    """
    if _debounce_lock.is_set():
        print(f"[Debounce] {trigger_type} dropped — still cooling down.")
        return

    global _pending_action
    _lock_debounce()

    _pending_action = {
        "trigger_type":     trigger_type,
        "audio_transcript": audio_transcript,
    }
    print(f"[Trigger] PENDING — {trigger_type}. Nod twice to confirm…")

    if _overlay:
        QMetaObject.invokeMethod(
            _overlay, "set_pending",
            Qt.QueuedConnection,
            Q_ARG(str, "NOD TWICE TO CONFIRM"),
        )
    if _controller:
        QMetaObject.invokeMethod(
            _controller, "start_timer",
            Qt.QueuedConnection,
        )


# ── Confirmation handlers ──────────────────────────────────────────────────
def _on_double_blink() -> None:
    """Called when the user nods twice (or double-blinks in future modes)."""
    global _pending_action
    if _pending_action is None:
        return  # No pending action — ignore spurious signals

    if _controller:
        QMetaObject.invokeMethod(
            _controller, "stop_timer",
            Qt.QueuedConnection,
        )
    action = _pending_action
    _pending_action = None
    _execute_action(action["trigger_type"], action["audio_transcript"])


def _execute_action(trigger_type: str, audio_transcript: str) -> None:
    """
    Fire screen capture + POST on a single background thread.

    Screen capture runs OFF the Qt main thread to keep the overlay
    responsive (no event-loop stall).
    """
    print(f"[Trigger] CONFIRMED — {trigger_type}. Capturing screen…")

    if _overlay:
        QMetaObject.invokeMethod(_overlay, "set_processing", Qt.QueuedConnection)

    def _on_success(data: dict) -> None:
        if _overlay:
            _overlay.response_ready.emit(data)
        _schedule_release()

    def _on_error(msg: str) -> None:
        if _overlay:
            _overlay.error_ready.emit(msg)
        _schedule_release()

    def _worker() -> None:
        """Runs entirely on a daemon thread — no Qt main-thread work here."""
        try:
            screen_b64 = capture_screen_b64()
        except RuntimeError as exc:
            print(f"[Capture] Failed: {exc}")
            screen_b64 = ""

        send_async(trigger_type, screen_b64, audio_transcript, _on_success, _on_error)
        print(f"[Network] POST dispatched — mock_mode={MOCK_MODE}")

    t = threading.Thread(target=_worker, daemon=True, name="SIE-CaptureAndSend")
    t.start()


# ── Keyboard trigger ───────────────────────────────────────────────────────
def _on_keyboard_trigger() -> None:
    """Registered hotkey callback — runs on the keyboard library thread."""
    _on_trigger("keyboard_hotkey")


def _quit_app() -> None:
    """Instantly kills the entire application from a global hotkey."""
    print(f"\n[System] Quit hotkey ({QUIT_HOTKEY}) pressed. Shutting down...")
    QApplication.instance().quit()


# ── Palm / audio gesture handlers ──────────────────────────────────────────
def _on_palm_opened() -> None:
    """Open palm: start push-to-talk recording."""
    if _debounce_lock.is_set() or not _mic_enabled:
        return
    if _audio:
        _audio.start_recording()
    if _overlay:
        QMetaObject.invokeMethod(_overlay, "set_listening", Qt.QueuedConnection)


def _on_palm_submitted() -> None:
    """Palm → fist transition: stop recording and submit the transcript."""
    if not _audio or not _audio.is_recording:
        return
    print("[Gesture] Palm submitted — stopping recording.")
    _audio.stop_recording()

    # Transcription is a blocking network call — run on a worker thread.
    def _transcribe_and_trigger() -> None:
        transcript = _audio.transcribe()
        _on_trigger("gesture_palm", transcript)

    t = threading.Thread(target=_transcribe_and_trigger, daemon=True, name="SIE-Transcribe")
    t.start()


def _on_palm_cancelled() -> None:
    """Palm → relaxed: discard recording and reset UI."""
    if not _audio or not _audio.is_recording:
        return
    print("[Gesture] Palm cancelled — discarding recording.")
    _audio.stop_recording()
    if _overlay:
        QMetaObject.invokeMethod(_overlay, "_dismiss", Qt.QueuedConnection)


def _on_fist_detected() -> None:
    """Fist: universal stop / dismiss."""
    global _pending_action

    # Stop any active recording without transcribing.
    if _audio and _audio.is_recording:
        _audio.stop_recording()

    # Cancel any pending action and release debounce.
    if _pending_action is not None:
        _pending_action = None
        if _controller:
            QMetaObject.invokeMethod(_controller, "stop_timer", Qt.QueuedConnection)
        _release_debounce()

    if _overlay:
        QMetaObject.invokeMethod(_overlay, "_dismiss", Qt.QueuedConnection)
    print("[Gesture] Fist — dismissed.")


# ── Face gesture handlers ─────────────────────────────────────────────────
def _on_head_nodded() -> None:
    """Head nod = confirm pending action."""
    _on_double_blink()


def _on_head_shaken() -> None:
    """Head shake = dismiss (natural 'no')."""
    _on_fist_detected()


def _on_jaw_opened() -> None:
    """Mouth opens = hands-free push-to-talk start."""
    _on_palm_opened()


def _on_jaw_closed() -> None:
    """Mouth closes after being open = hands-free push-to-talk submit."""
    _on_palm_submitted()


def _on_frustration_detected() -> None:
    """
    Sustained brow furrow = user confused by last response.
    Automatically sends a clarification request to the backend.
    """
    if _debounce_lock.is_set():
        return
    print("[Face] Frustration detected — sending auto-clarify.")
    _on_trigger("frustration_clarify", "Please explain that more clearly and simply.")


def _on_drowsy_alert() -> None:
    """PERCLOS threshold hit — show a wellness notification."""
    print("[Face] Drowsiness detected — showing wellness alert.")
    if _overlay:
        QMetaObject.invokeMethod(
            _overlay, "show_wellness_alert",
            Qt.QueuedConnection,
            Q_ARG(str, "You look tired. Consider a short break 💫"),
        )


def _on_gaze_changed(on_screen: bool) -> None:
    """Gaze on/off screen — pause or resume the result card dismiss timer."""
    if _overlay:
        QMetaObject.invokeMethod(
            _overlay, "on_gaze_changed",
            Qt.QueuedConnection,
            Q_ARG(bool, on_screen),
        )


# ── System Tray ────────────────────────────────────────────────────────────
def _setup_tray(app: QApplication) -> QSystemTrayIcon:
    icon = app.style().standardIcon(QStyle.SP_ComputerIcon)
    tray = QSystemTrayIcon(icon, app)
    menu = QMenu()

    cam_action = QAction("Show Camera Feed", checkable=True)
    cam_action.setChecked(True)
    def _toggle_cam(checked: bool) -> None:
        if _overlay:
            _overlay._camera_hud.setVisible(checked)
    cam_action.toggled.connect(_toggle_cam)

    mic_action = QAction("Enable Microphone", checkable=True)
    mic_action.setChecked(True)
    def _toggle_mic(checked: bool) -> None:
        global _mic_enabled
        _mic_enabled = checked
        if not checked and _audio and _audio.is_recording:
            _audio.stop_recording()
            if _overlay:
                QMetaObject.invokeMethod(_overlay, "_dismiss", Qt.QueuedConnection)
    mic_action.toggled.connect(_toggle_mic)

    quit_action = QAction("Quit Engine")
    quit_action.triggered.connect(app.quit)

    menu.addAction(cam_action)
    menu.addAction(mic_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    tray.setToolTip("Spatial Intent Engine — Lemihandle")
    tray.show()
    return tray


# ── Application bootstrap ──────────────────────────────────────────────────
def main() -> None:
    global _overlay, _gesture, _audio, _controller, _tray

    print("=" * 60)
    print("  SPATIAL INTENT ENGINE — Lemihandle Frontend")
    print(f"  Mock mode        : {MOCK_MODE}")
    print(f"  Hotkey (Trigger) : {HOTKEY}")
    print(f"  Hotkey (Quit)    : {QUIT_HOTKEY}")
    print("=" * 60)

    app = QApplication(sys.argv)
    app.setApplicationName("SpatialIntentEngine")
    app.setApplicationDisplayName("Gemini.exe — Spatial Intent Engine")
    # Keep the app alive even when all windows are closed (tray keeps it running)
    app.setQuitOnLastWindowClosed(False)

    # Controller must be created before any signals are connected.
    _controller = AppController()

    _tray = _setup_tray(app)

    # ── Overlay ──────────────────────────────────────────────────────────
    _overlay = SIEOverlay()
    _overlay.show()

    # ── Audio engine ─────────────────────────────────────────────────────
    _audio = AudioEngine()

    # ── Gesture engine ────────────────────────────────────────────────────
    _gesture = GestureEngine()
    _gesture.pinch_detected.connect(lambda: _on_trigger("gesture_pinch"))
    _gesture.palm_opened.connect(_on_palm_opened)
    _gesture.palm_submitted.connect(_on_palm_submitted)
    _gesture.palm_cancelled.connect(_on_palm_cancelled)
    _gesture.fist_detected.connect(_on_fist_detected)
    _gesture.frame_ready.connect(_overlay.update_camera_frame)
    # Face signals
    _gesture.head_nodded.connect(_on_head_nodded)
    _gesture.head_shaken.connect(_on_head_shaken)
    _gesture.jaw_opened.connect(_on_jaw_opened)
    _gesture.jaw_closed.connect(_on_jaw_closed)
    _gesture.frustration_detected.connect(_on_frustration_detected)
    _gesture.drowsy_alert.connect(_on_drowsy_alert)
    _gesture.gaze_on_card.connect(_on_gaze_changed)
    _gesture.start()

    # ── Keyboard hooks ────────────────────────────────────────────────────
    keyboard.add_hotkey(HOTKEY, _on_keyboard_trigger)
    keyboard.add_hotkey(QUIT_HOTKEY, _quit_app)
    print("[Keyboard] Hotkeys registered.")

    # ── Event loop ────────────────────────────────────────────────────────
    exit_code = app.exec_()

    # ── Teardown ──────────────────────────────────────────────────────────
    keyboard.remove_all_hotkeys()
    if _audio and _audio.is_recording:
        _audio.stop_recording()
    if _gesture:
        _gesture.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
