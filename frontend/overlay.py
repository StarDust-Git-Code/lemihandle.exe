# overlay.py — Transparent OS overlay + Render Engine (Skills 1 & 5)
# =========================================================================
# A borderless, full-screen PyQt5 window that is fully click-through in the
# IDLE state.  Transitions through PROCESSING and RESULT states with smooth
# animations, then auto-dismisses after RESULT_DISPLAY_MS milliseconds.

import ctypes
import ctypes.wintypes
import sys

from PyQt5.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QTextDocument,
    QImage,
    QPixmap
)
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel

from constants import (
    BG_COLOR,
    FADE_DURATION_MS,
    FONT_FAMILY,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    NEON_COLOR,
    RESULT_DISPLAY_MS,
    SPINNER_FRAMES,
)

# ── Windows API helpers ───────────────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020


def _apply_click_through(hwnd: int) -> None:
    """Inject WS_EX_TRANSPARENT | WS_EX_LAYERED into the window extended style."""
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current | WS_EX_LAYERED | WS_EX_TRANSPARENT)


def _remove_click_through(hwnd: int) -> None:
    """Remove WS_EX_TRANSPARENT so the result card can be interacted with."""
    if sys.platform != "win32":
        return
    user32 = ctypes.windll.user32
    current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current & ~WS_EX_TRANSPARENT)


# ── Overlay states ────────────────────────────────────────────────────────
class _State:
    IDLE       = "idle"
    PROCESSING = "processing"
    LISTENING  = "listening"
    PENDING    = "pending"
    RESULT     = "result"
    ERROR      = "error"
    WELLNESS   = "wellness"


# ── Canvas widget (inner painter surface) ─────────────────────────────────
class _OverlayCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._state      = _State.IDLE
        self._result_text = ""
        self._pending_message = ""
        self._spinner_idx = 0
        self._is_error    = False

        # Spinner animation timer
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(130)
        self._spinner_timer.timeout.connect(self._advance_spinner)

    # ── State API ──────────────────────────────────────────────────────────

    def set_idle(self):
        self._spinner_timer.stop()
        self._state = _State.IDLE
        self.update()

    def set_processing(self):
        self._spinner_timer.start()
        self._state = _State.PROCESSING
        self.update()

    def set_listening(self):
        self._spinner_timer.start()
        self._state = _State.LISTENING
        self.update()

    def set_pending(self, message: str):
        self._spinner_timer.start()
        self._state = _State.PENDING
        self._pending_message = message
        self.update()

    def set_result(self, text: str, is_error: bool = False):
        self._spinner_timer.stop()
        self._result_text = text
        self._is_error    = is_error
        self._state       = _State.RESULT
        self.update()

    # ── Spinner helper ─────────────────────────────────────────────────────

    def _advance_spinner(self):
        self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER_FRAMES)
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, _event):  # noqa: N802
        if self._state == _State.IDLE:
            return  # Completely invisible

        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform
        )

        if self._state == _State.PROCESSING:
            self._draw_processing_pill(painter, "Gemini is reasoning…")
        elif self._state == _State.LISTENING:
            self._draw_processing_pill(painter, "Listening…")
        elif self._state == _State.PENDING:
            self._draw_processing_pill(painter, self._pending_message)
        elif self._state == _State.WELLNESS:
            self._draw_wellness_pill(painter, self._pending_message)
        elif self._state in (_State.RESULT, _State.ERROR):
            self._draw_result_card(painter)

        painter.end()

    def _draw_processing_pill(self, painter: QPainter, text: str):
        """Small animated pill in the top-right corner."""
        sw, sh = self.width(), self.height()
        pw, ph = 320, 52
        px = sw - pw - 32
        py = 32

        rect = QRectF(px, py, pw, ph)
        path = QPainterPath()
        path.addRoundedRect(rect, ph / 2, ph / 2)

        painter.save()
        painter.fillPath(path, QColor(10, 10, 25, 230))
        pen = QPen(QColor(*NEON_COLOR, 180), 1.5)
        painter.setPen(pen)
        painter.drawPath(path)
        frame = SPINNER_FRAMES[self._spinner_idx]
        font = QFont(FONT_FAMILY, FONT_SIZE_TITLE, QFont.Medium)
        painter.setFont(font)
        painter.setPen(QColor(*NEON_COLOR))
        painter.drawText(rect, Qt.AlignCenter, f"{frame}  {text}")
        painter.restore()

    def _draw_wellness_pill(self, painter: QPainter, text: str):
        """Amber wellness notification pill in the bottom-centre."""
        sw, sh = self.width(), self.height()
        pw, ph = 380, 52
        px = (sw - pw) // 2
        py = sh - ph - 48

        rect = QRectF(px, py, pw, ph)
        path = QPainterPath()
        path.addRoundedRect(rect, ph / 2, ph / 2)

        painter.save()
        painter.fillPath(path, QColor(25, 18, 5, 230))
        pen = QPen(QColor(255, 180, 0, 200), 1.5)
        painter.setPen(pen)
        painter.drawPath(path)
        font = QFont(FONT_FAMILY, FONT_SIZE_TITLE, QFont.Medium)
        painter.setFont(font)
        painter.setPen(QColor(255, 200, 60))
        painter.drawText(rect, Qt.AlignCenter, f"🌿  {text}")
        painter.restore()

    def _draw_result_card(self, painter: QPainter):
        """Full glassmorphism floating card in the center-right of the screen."""
        sw, sh = self.width(), self.height()
        cw, ch = 520, min(sh - 120, 520)
        cx = sw - cw - 48
        cy = (sh - ch) // 2

        rect  = QRectF(cx, cy, cw, ch)
        path  = QPainterPath()
        path.addRoundedRect(rect, 18, 18)

        # ── Background ──────────────────────────────────────────────────
        painter.save()
        bg = QColor(*BG_COLOR)
        painter.fillPath(path, bg)

        # Subtle gradient overlay (top lighter stripe)
        grad = QLinearGradient(cx, cy, cx, cy + ch * 0.35)
        grad.setColorAt(0, QColor(255, 255, 255, 14))
        grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillPath(path, grad)

        # ── Neon border ─────────────────────────────────────────────────
        accent = QColor(220, 80, 80) if self._is_error else QColor(*NEON_COLOR)
        # Outer glow pass
        glow_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 40), 8)
        painter.setPen(glow_pen)
        painter.drawPath(path)
        # Inner crisp border
        border_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 200), 1.5)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # ── Top accent bar ───────────────────────────────────────────────
        bar_path = QPainterPath()
        bar_path.addRoundedRect(QRectF(cx + 1.5, cy + 1.5, cw - 3, 4), 2, 2)
        painter.fillPath(bar_path, accent)

        # ── Title ────────────────────────────────────────────────────────
        title_font = QFont(FONT_FAMILY, FONT_SIZE_TITLE, QFont.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(accent))
        title_label = "⚠  Error" if self._is_error else "✦  Gemini Spatial Response"
        painter.drawText(
            QRectF(cx + 22, cy + 18, cw - 44, 28),
            Qt.AlignLeft | Qt.AlignVCenter,
            title_label,
        )

        # ── Divider ──────────────────────────────────────────────────────
        painter.setPen(QPen(QColor(*NEON_COLOR, 45), 1))
        painter.drawLine(int(cx + 22), int(cy + 50), int(cx + cw - 22), int(cy + 50))

        # ── Body text (word-wrapped via QTextDocument) ───────────────────
        doc = QTextDocument()
        doc.setDefaultFont(QFont(FONT_FAMILY, FONT_SIZE_BODY))
        doc.setDefaultStyleSheet(
            "body { color: #d0e8e4; line-height: 165%; }"
            "b    { color: #00f0c8; }"
        )
        doc.setHtml(f"<body>{self._result_text.replace(chr(10), '<br>')}</body>")
        doc.setTextWidth(cw - 52)

        painter.translate(cx + 26, cy + 60)
        clip = QRectF(0, 0, cw - 52, ch - 80)
        painter.setClipRect(clip)
        doc.drawContents(painter, clip)

        painter.restore()


# ── Main overlay window ───────────────────────────────────────────────────
class SIEOverlay(QMainWindow):
    """
    Top-level borderless full-screen window.

    Signals
    -------
    response_ready : pyqtSignal(dict)
        Emitted from the network thread; connected to on_response_received.
    error_ready    : pyqtSignal(str)
        Emitted from the network thread on failure.
    trigger_fired  : pyqtSignal(str)
        Connected to the controller; carries trigger_type string.
    """

    response_ready = pyqtSignal(dict)
    error_ready    = pyqtSignal(str)
    trigger_fired  = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        # ── Window flags ─────────────────────────────────────────────────
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # ── Canvas ───────────────────────────────────────────────────────
        self._canvas = _OverlayCanvas(self)
        self._canvas.setGeometry(0, 0, screen.width(), screen.height())
        self.setCentralWidget(self._canvas)

        # ── Camera HUD ───────────────────────────────────────────────────
        self._camera_hud = QLabel(self)
        # Positioned bottom-left
        self._camera_hud.setGeometry(32, screen.height() - 240 - 32, 320, 240)
        self._camera_hud.setStyleSheet("border: 2px solid #00f0c8; border-radius: 8px; background: rgba(0,0,0,150);")
        self._camera_hud.raise_()

        # ── Fade animation ───────────────────────────────────────────────
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(FADE_DURATION_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # ── Auto-dismiss timer ───────────────────────────────────────────
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._dismiss)

        # ── Connect internal signals ─────────────────────────────────────
        self.response_ready.connect(self.on_response_received)
        self.error_ready.connect(self.on_error_received)

        self._hwnd: int | None = None

    def show(self) -> None:  # noqa: A003
        super().show()
        self._hwnd = int(self.winId())
        _apply_click_through(self._hwnd)   # IDLE: clicks fall through

    # ── State transitions ─────────────────────────────────────────────────

    @pyqtSlot()
    def set_processing(self) -> None:
        self._dismiss_timer.stop()
        self.setWindowOpacity(1.0)
        self._canvas.set_processing()
        # Keep click-through during processing so user can keep working
        if self._hwnd:
            _apply_click_through(self._hwnd)

    @pyqtSlot()
    def set_listening(self) -> None:
        self._dismiss_timer.stop()
        self.setWindowOpacity(1.0)
        self._canvas.set_listening()
        if self._hwnd:
            _apply_click_through(self._hwnd)

    @pyqtSlot(str)
    def set_pending(self, message: str) -> None:
        self._dismiss_timer.stop()
        self.setWindowOpacity(1.0)
        self._canvas.set_pending(message)
        if self._hwnd:
            _apply_click_through(self._hwnd)

    @pyqtSlot(bool)
    def on_gaze_changed(self, on_screen: bool) -> None:
        """Pause or resume the result auto-dismiss timer based on attention."""
        if self._canvas._state not in (_State.RESULT, _State.ERROR):
            return
        if on_screen:
            self._dismiss_timer.start()   # resume countdown
        else:
            self._dismiss_timer.stop()    # pause — user looked away

    @pyqtSlot(str)
    def show_wellness_alert(self, message: str) -> None:
        """Show a non-intrusive amber wellness pill at the bottom of screen."""
        self.setWindowOpacity(1.0)
        self._canvas._pending_message = message
        self._canvas._state = _State.WELLNESS
        self._canvas.update()
        # Auto-dismiss after 6 s if not already in a result state
        QTimer.singleShot(6000, self._clear_wellness)

    def _clear_wellness(self) -> None:
        if self._canvas._state == _State.WELLNESS:
            self._canvas.set_idle()
            self.setWindowOpacity(1.0)
            if self._hwnd:
                _apply_click_through(self._hwnd)

    @pyqtSlot(QImage)
    def update_camera_frame(self, image: QImage) -> None:
        if self._camera_hud.isHidden():
            return
        pixmap = QPixmap.fromImage(image).scaled(320, 240, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._camera_hud.setPixmap(pixmap)

    @pyqtSlot(dict)
    def on_response_received(self, data: dict) -> None:
        text = data.get("ai_output", "(no response)")
        self._show_result(text, is_error=False)

    @pyqtSlot(str)
    def on_error_received(self, message: str) -> None:
        self._show_result(message, is_error=True)

    def _show_result(self, text: str, is_error: bool) -> None:
        self._canvas.set_result(text, is_error)
        # Remove click-through so the card is interactable (future: click-to-copy)
        if self._hwnd:
            _remove_click_through(self._hwnd)
        self._fade_in()
        self._dismiss_timer.start(RESULT_DISPLAY_MS)

    @pyqtSlot()
    def _dismiss(self) -> None:
        self._fade_out_then_idle()

    def _fade_in(self) -> None:
        # Disconnect any lingering finished handler before starting fade-in
        try:
            self._anim.finished.disconnect()
        except TypeError:
            pass
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _fade_out_then_idle(self) -> None:
        # Always disconnect first — prevents the signal from accumulating
        # handlers across multiple dismiss/show cycles (the flicker bug).
        try:
            self._anim.finished.disconnect()
        except TypeError:
            pass
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._reset_to_idle)
        self._anim.start()

    def _reset_to_idle(self) -> None:
        # Disconnect guard — should already be disconnected but be defensive
        try:
            self._anim.finished.disconnect()
        except TypeError:
            pass
        self._canvas.set_idle()
        self._dismiss_timer.stop()
        # Do NOT set windowOpacity here — it causes a one-frame flash.
        # The next _fade_in() will set the correct start value from whatever
        # opacity the window currently has.
        if self._hwnd:
            _apply_click_through(self._hwnd)

    # ── Keyboard event (optional Escape to dismiss) ───────────────────────
    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self._dismiss_timer.stop()
            self._reset_to_idle()
        super().keyPressEvent(event)
