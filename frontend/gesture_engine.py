"""
gesture_engine.py — MediaPipe tracking thread (Hand + Face)
============================================================

Hand signals
------------
  pinch_detected   → screenshot trigger
  palm_opened      → start push-to-talk recording
  palm_submitted   → stop recording and submit (palm → fist)
  palm_cancelled   → stop recording and discard (palm → relax)
  fist_detected    → universal dismiss

Face signals
------------
  head_nodded          → confirm pending action  (replaces double-blink)
  head_shaken          → dismiss                 (natural "no")
  jaw_opened           → hands-free PTT start    (mouth-open recording)
  jaw_closed           → hands-free PTT submit   (mouth-close after open)
  frustration_detected → sustained brow furrow → backend will auto-clarify
  drowsy_alert         → PERCLOS threshold hit → wellness notification
  gaze_on_card(bool)   → True = looking at screen, False = looked away

Camera
------
  frame_ready(QImage) → every frame → PIP HUD in overlay
"""

import collections
import math
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from constants import CAMERA_INDEX, PINCH_THRESHOLD_PX

# ── Thresholds ────────────────────────────────────────────────────────────
_EAR_BLINK       = 0.20   # eye aspect ratio below this = closed
_EAR_DROWSY_PCT  = 0.25   # PERCLOS: >25% closed in window = drowsy
_JAW_OPEN_TH     = 0.40   # jawOpen blendshape score (lowered — 0.55 was too high)
_JAW_CLOSE_TH    = 0.15
_BROW_DOWN_TH    = 0.45   # frustration: both brows down above this
_BROW_SUSTAIN_S  = 2.5    # seconds sustained to fire frustration
_NOD_DIP_TH      = 0.035  # normalised nose-y delta for a single nod dip
_NOD_WINDOW_S    = 1.8    # two dips must happen within this window
_SHAKE_SWING_TH  = 0.055  # normalised nose-x swing for one direction change
_SHAKE_WINDOW_S  = 1.8    # full left-right-left (or right-left-right) within


class GestureEngine(QThread):

    # ── Hand signals ──────────────────────────────────────────────────────
    pinch_detected  = pyqtSignal()
    palm_opened     = pyqtSignal()
    palm_submitted  = pyqtSignal()
    palm_cancelled  = pyqtSignal()
    fist_detected   = pyqtSignal()

    # ── Face signals ──────────────────────────────────────────────────────
    head_nodded          = pyqtSignal()
    head_shaken          = pyqtSignal()
    jaw_opened           = pyqtSignal()
    jaw_closed           = pyqtSignal()
    frustration_detected = pyqtSignal()
    drowsy_alert         = pyqtSignal()
    gaze_on_card         = pyqtSignal(bool)

    # ── Camera feed ───────────────────────────────────────────────────────
    frame_ready = pyqtSignal(QImage)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._running       = True
        self._paused        = False

        # ── Hand state ───────────────────────────────────────────────────
        self._is_palm_open  = False
        self._fist_cooldown = 0.0

        # ── Face: nod ────────────────────────────────────────────────────
        self._nod_count      = 0
        self._nod_was_down   = False
        self._last_nod_time  = 0.0
        self._nod_baseline   = None   # set from first real frame, not guessed

        # ── Face: shake ──────────────────────────────────────────────────
        self._shake_changes   = 0
        self._shake_last_dir  = 0     # -1 left, 0 centre, 1 right
        self._last_shake_time = 0.0
        self._shake_baseline  = None  # set from first real frame

        # ── Face: jaw (hands-free PTT) ───────────────────────────────────
        self._jaw_is_open    = False
        self._jaw_cooldown   = 0.0

        # ── Face: frustration ─────────────────────────────────────────────
        self._frustration_start    = 0.0
        self._frustration_active   = False
        self._frustration_cooldown = 0.0

        # ── Face: drowsiness (PERCLOS) ───────────────────────────────────
        # ~15 fps camera × 30 s = 450 frames rolling window
        self._ear_window      = collections.deque(maxlen=450)
        self._drowsy_cooldown = 0.0

        # ── Face: gaze / attention ────────────────────────────────────────
        self._last_gaze_on = True   # track state to avoid duplicate signals

        # ── MediaPipe: Hand Landmarker ────────────────────────────────────
        hand_base = python.BaseOptions(model_asset_path='hand_landmarker.task')
        hand_opts = vision.HandLandmarkerOptions(
            base_options=hand_base,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
            running_mode=vision.RunningMode.VIDEO,
        )
        self._hand_lmk = vision.HandLandmarker.create_from_options(hand_opts)

        # ── MediaPipe: Face Landmarker ────────────────────────────────────
        face_base = python.BaseOptions(model_asset_path='face_landmarker.task')
        face_opts = vision.FaceLandmarkerOptions(
            base_options=face_base,
            num_faces=1,
            output_face_blendshapes=True,   # required for jaw/brow features
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.VIDEO,
        )
        self._face_lmk = vision.FaceLandmarker.create_from_options(face_opts)

    # ── Public API ────────────────────────────────────────────────────────

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._running = False
        self.wait()

    # ── QThread main loop ─────────────────────────────────────────────────

    def run(self) -> None:
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            print(f"[GestureEngine] WARNING: Cannot open camera {CAMERA_INDEX}. "
                  "Use Ctrl+Shift+Space instead.")
            return

        try:
            while self._running:
                if self._paused:
                    time.sleep(0.05)
                    continue

                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue

                frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                h, w = frame_rgb.shape[:2]

                mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                ts_ms   = int(time.time() * 1000)

                hand_r = self._hand_lmk.detect_for_video(mp_img, ts_ms)
                face_r = self._face_lmk.detect_for_video(mp_img, ts_ms)

                self._process_hands(hand_r, frame_rgb, h, w)
                self._process_face(face_r, frame_rgb, h, w)

                bpl   = 3 * w
                q_img = QImage(frame_rgb.data, w, h, bpl, QImage.Format_RGB888)
                self.frame_ready.emit(q_img)

        finally:
            cap.release()
            self._hand_lmk.close()
            self._face_lmk.close()

    # ── Hand processing ───────────────────────────────────────────────────

    def _process_hands(self, results, frame_rgb, h, w) -> None:
        is_palm_now = False

        if results.hand_landmarks:
            lm = results.hand_landmarks[0]

            def dist(a: int, b: int) -> float:
                return math.sqrt(
                    ((lm[a].x - lm[b].x) * w) ** 2 +
                    ((lm[a].y - lm[b].y) * h) ** 2
                )

            if dist(4, 8) < PINCH_THRESHOLD_PX:
                self.pinch_detected.emit()
                time.sleep(0.15)
            else:
                norm = dist(0, 9)
                if norm > 0:
                    ratio = sum(dist(0, t) for t in [8, 12, 16, 20]) / (4.0 * norm)
                    if ratio > 1.7:
                        is_palm_now = True
                    elif ratio < 1.2 and time.time() > self._fist_cooldown:
                        self.fist_detected.emit()
                        self._fist_cooldown = time.time() + 1.5

            # Draw cyberpunk skeleton
            BONES = [
                (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
                (13,17),(0,17),(17,18),(18,19),(19,20),
            ]
            for a, b in BONES:
                p1 = (int(lm[a].x * w), int(lm[a].y * h))
                p2 = (int(lm[b].x * w), int(lm[b].y * h))
                cv2.line(frame_rgb, p1, p2, (255, 100, 50), 1)
            for i in range(21):
                cv2.circle(frame_rgb,
                           (int(lm[i].x * w), int(lm[i].y * h)),
                           3, (0, 240, 200), -1)

        # Palm state machine
        if is_palm_now:
            if not self._is_palm_open:
                self._is_palm_open = True
                self.palm_opened.emit()
        else:
            if self._is_palm_open:
                self._is_palm_open = False
                is_fist = False
                if results.hand_landmarks:
                    lm2 = results.hand_landmarks[0]
                    def dist2(a: int, b: int) -> float:
                        return math.sqrt(
                            ((lm2[a].x - lm2[b].x) * w) ** 2 +
                            ((lm2[a].y - lm2[b].y) * h) ** 2
                        )
                    n = dist2(0, 9)
                    if n > 0 and sum(dist2(0, t) for t in [8,12,16,20]) / (4*n) < 1.2:
                        is_fist = True
                if is_fist:
                    self.palm_submitted.emit()
                    self._fist_cooldown = time.time() + 1.0
                else:
                    self.palm_cancelled.emit()

    # ── Face processing ───────────────────────────────────────────────────

    def _process_face(self, results, frame_rgb, h, w) -> None:
        now = time.time()

        if not results.face_landmarks:
            # Face gone → user is not looking at screen
            if self._last_gaze_on:
                self._last_gaze_on = False
                self.gaze_on_card.emit(False)
            return

        lm = results.face_landmarks[0]

        # Parse blendshapes → {name: score}
        bs: dict[str, float] = {}
        if results.face_blendshapes:
            for cat in results.face_blendshapes[0]:
                bs[cat.category_name] = cat.score

        # Draw eye tracking dots (neon purple)
        for idx in [33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380]:
            cv2.circle(frame_rgb,
                       (int(lm[idx].x * w), int(lm[idx].y * h)),
                       2, (200, 0, 240), -1)

        # ── EAR → drowsiness ─────────────────────────────────────────────
        ear = self._calc_ear(lm, w, h)
        self._ear_window.append(ear)
        self._check_drowsiness(now)

        # ── Gaze / attention ─────────────────────────────────────────────
        self._check_gaze(lm, now)

        # ── Head nod (confirm) ────────────────────────────────────────────
        self._check_nod(lm[4].y, now)      # landmark 4 = nose tip

        # ── Head shake (dismiss) ──────────────────────────────────────────
        self._check_shake(lm[4].x, lm, now)

        # ── Jaw open — hands-free PTT ─────────────────────────────────────
        if bs:
            self._check_jaw(bs, now)
            self._check_frustration(bs, now)

    # ── Face feature helpers ──────────────────────────────────────────────

    def _calc_ear(self, lm, w: int, h: int) -> float:
        """Eye Aspect Ratio averaged over both eyes."""
        def ear(pts):
            p = [lm[i] for i in pts]
            def d(a, b):
                return math.sqrt(((a.x-b.x)*w)**2 + ((a.y-b.y)*h)**2)
            v1, v2 = d(p[1], p[5]), d(p[2], p[4])
            hz = d(p[0], p[3])
            return (v1 + v2) / (2.0 * hz) if hz > 0 else 0.3
        return (ear([33,160,158,133,153,144]) + ear([362,385,387,263,373,380])) / 2

    def _check_drowsiness(self, now: float) -> None:
        """PERCLOS: if >25% of the last 30 s window has EAR < threshold → alert."""
        if len(self._ear_window) < 100:     # need enough samples first
            return
        closed_pct = sum(1 for e in self._ear_window if e < _EAR_BLINK) / len(self._ear_window)
        if closed_pct > _EAR_DROWSY_PCT and now > self._drowsy_cooldown:
            self._drowsy_cooldown = now + 120.0     # alert at most once per 2 min
            self.drowsy_alert.emit()

    def _check_gaze(self, lm, now: float) -> None:
        """
        Attention proxy: estimate yaw and pitch from nose vs. ear positions.
        If face is roughly facing forward → user is on screen.
        """
        nose_x  = lm[4].x
        l_ear_x = lm[234].x
        r_ear_x = lm[454].x
        face_w  = abs(l_ear_x - r_ear_x)
        if face_w < 0.01:
            return
        # Signed yaw ratio: 0 = forward, ±1 = fully turned
        mid_x   = (l_ear_x + r_ear_x) / 2
        yaw_ratio = abs(nose_x - mid_x) / (face_w * 0.5)

        # Pitch: compare nose-y to eye-midpoint-y
        eye_mid_y = (lm[33].y + lm[263].y) / 2
        pitch_drop = lm[4].y - eye_mid_y     # positive = looking down

        on_screen = (yaw_ratio < 0.4 and pitch_drop < 0.25)

        if on_screen != self._last_gaze_on:
            self._last_gaze_on = on_screen
            self.gaze_on_card.emit(on_screen)

    def _check_nod(self, nose_y: float, now: float) -> None:
        """Two downward dips of the nose within _NOD_WINDOW_S → head_nodded."""
        # Initialise baseline from the very first real nose position
        if self._nod_baseline is None:
            self._nod_baseline = nose_y
            return

        # Slow drift to follow natural head position changes
        self._nod_baseline = self._nod_baseline * 0.97 + nose_y * 0.03

        dipped = nose_y > self._nod_baseline + _NOD_DIP_TH

        if dipped and not self._nod_was_down:
            self._nod_was_down = True
            if now - self._last_nod_time < _NOD_WINDOW_S:
                self._nod_count += 1
            else:
                self._nod_count = 1
            self._last_nod_time = now
            print(f"[Face] Nod dip detected (count={self._nod_count}, baseline={self._nod_baseline:.3f}, nose_y={nose_y:.3f})")
            if self._nod_count >= 2:
                self._nod_count = 0
                self._last_nod_time = 0.0
                print("[Face] HEAD NOD confirmed — emitting head_nodded")
                self.head_nodded.emit()
        elif not dipped:
            self._nod_was_down = False

    def _check_shake(self, nose_x: float, lm, now: float) -> None:
        """One left-right oscillation within _SHAKE_WINDOW_S → head_shaken."""
        # Initialise baseline from first real frame
        if self._shake_baseline is None:
            self._shake_baseline = nose_x
            return

        self._shake_baseline = self._shake_baseline * 0.97 + nose_x * 0.03
        delta = nose_x - self._shake_baseline

        if delta > _SHAKE_SWING_TH:
            cur_dir = 1
        elif delta < -_SHAKE_SWING_TH:
            cur_dir = -1
        else:
            return   # still in centre band

        if cur_dir != self._shake_last_dir and self._shake_last_dir != 0:
            if now - self._last_shake_time > _SHAKE_WINDOW_S:
                self._shake_changes = 0
            self._shake_changes    += 1
            self._last_shake_time   = now
            print(f"[Face] Shake direction change (count={self._shake_changes})")
            if self._shake_changes >= 2:
                self._shake_changes = 0
                print("[Face] HEAD SHAKE confirmed — emitting head_shaken")
                self.head_shaken.emit()

        self._shake_last_dir = cur_dir

    def _check_jaw(self, bs: dict, now: float) -> None:
        """jawOpen blendshape thresholds → jaw_opened / jaw_closed signals."""
        score = bs.get("jawOpen", 0.0)
        if score > _JAW_OPEN_TH and not self._jaw_is_open and now > self._jaw_cooldown:
            self._jaw_is_open = True
            print(f"[Face] JAW OPENED (score={score:.2f}) — emitting jaw_opened")
            self.jaw_opened.emit()
        elif score < _JAW_CLOSE_TH and self._jaw_is_open:
            self._jaw_is_open  = False
            self._jaw_cooldown = now + 2.0   # prevent immediate re-trigger
            print(f"[Face] JAW CLOSED (score={score:.2f}) — emitting jaw_closed")
            self.jaw_closed.emit()

    def _check_frustration(self, bs: dict, now: float) -> None:
        """Both brows furrowed for _BROW_SUSTAIN_S seconds → frustration_detected."""
        brow_l = bs.get("browDownLeft",  0.0)
        brow_r = bs.get("browDownRight", 0.0)
        frowning = (brow_l > _BROW_DOWN_TH and brow_r > _BROW_DOWN_TH)

        if frowning:
            if not self._frustration_active:
                self._frustration_active = True
                self._frustration_start  = now
            elif (now - self._frustration_start > _BROW_SUSTAIN_S
                  and now > self._frustration_cooldown):
                self._frustration_cooldown = now + 30.0  # once per 30 s max
                self._frustration_active   = False
                self.frustration_detected.emit()
        else:
            self._frustration_active = False
