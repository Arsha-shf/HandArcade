"""
engine/head_tracking.py

MediaPipe face-tracking wrapper shared by any HandArcade game that steers
with head position instead of hand position (e.g. Dodge).

Mirrors the structure of engine/tracking.py (HandTracker) so games can be
written the same way regardless of which body part drives them: a thin
wrapper around the MediaPipe Tasks API, with proxy objects that give a
stable, easy-to-read interface.

Usage:
    from engine.head_tracking import HeadTracker, get_head_position, SmoothedValue

    tracker = HeadTracker()
    results = tracker.process(frame)  # frame = BGR image from cv2

    if results.multi_face_landmarks:
        face_landmarks = results.multi_face_landmarks[0]
        x, y = get_head_position(face_landmarks, frame.shape)

    # Optional: smooth the x position frame-to-frame to kill jitter
    smoother = SmoothedValue(alpha=0.3)
    smooth_x = smoother.update(x)
"""

import os

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# Model file downloaded once via:
#   wget -O engine/models/face_landmarker.task \
#     https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "models", "face_landmarker.task"
)

# Landmark indices (MediaPipe FaceMesh 478-point topology, same indices
# the Face Landmarker task uses).
NOSE_TIP = 1
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263
FOREHEAD = 10
CHIN = 152


class _FaceLandmarksProxy:
    """Mimics a simple NormalizedLandmarkList: exposes `.landmark` as a list of points."""

    __slots__ = ("landmark",)

    def __init__(self, landmark_list):
        self.landmark = landmark_list


class _ResultsProxy:
    """Mimics the old mp.solutions-style `results` object: `.multi_face_landmarks`."""

    __slots__ = ("multi_face_landmarks",)

    def __init__(self, task_result):
        faces = [_FaceLandmarksProxy(f) for f in task_result.face_landmarks]
        self.multi_face_landmarks = faces or None


class HeadTracker:
    """Thin wrapper around mp.tasks.vision.FaceLandmarker with a HandTracker-like interface."""

    def __init__(
        self,
        max_num_faces=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        static_image_mode=False,
        model_path=_DEFAULT_MODEL_PATH,
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Face landmark model not found at {model_path}. "
                "Download it with:\n"
                "  wget -O engine/models/face_landmarker.task "
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
                "face_landmarker/float16/1/face_landmarker.task"
            )

        self._static_image_mode = static_image_mode
        running_mode = (
            mp_vision.RunningMode.IMAGE if static_image_mode else mp_vision.RunningMode.VIDEO
        )

        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=running_mode,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            # Landmark output only; we don't need blendshapes or the
            # facial transformation matrix for steering a game character.
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        self._frame_count = 0

    def process(self, frame_bgr):
        """
        Run face detection on a BGR frame (as read by cv2.VideoCapture).
        Returns a proxy object with .multi_face_landmarks, matching the
        shape HandTracker.process() returns for hands.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        if self._static_image_mode:
            result = self._landmarker.detect(mp_image)
        else:
            self._frame_count += 1  # just needs to be monotonically increasing
            result = self._landmarker.detect_for_video(mp_image, self._frame_count)

        return _ResultsProxy(result)

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def _to_pixel(landmark, frame_shape):
    """Convert a normalized MediaPipe landmark (0-1 range) to pixel coords."""
    h, w = frame_shape[:2]
    return int(landmark.x * w), int(landmark.y * h)


def get_head_position(face_landmarks, frame_shape=None, landmark=NOSE_TIP):
    """
    Return the position of a single stable point on the head (nose tip by
    default -- picked because it barely moves relative to the skull even
    as the face tilts or turns, which makes it the steadiest thing to
    drive character x-position from).

    If frame_shape is given (e.g. frame.shape from cv2), returns pixel
    (x, y) ints. Otherwise returns normalized (x, y) floats in [0, 1].
    """
    lm = face_landmarks.landmark[landmark]
    if frame_shape is not None:
        return _to_pixel(lm, frame_shape)
    return (lm.x, lm.y)


def get_face_center(face_landmarks, frame_shape=None):
    """
    Approximate the face center as the midpoint of forehead and chin,
    which is more resistant to single-landmark noise than any one point.

    Returns pixel (x, y) if frame_shape given, else normalized (x, y).
    """
    forehead = face_landmarks.landmark[FOREHEAD]
    chin = face_landmarks.landmark[CHIN]
    cx = (forehead.x + chin.x) / 2
    cy = (forehead.y + chin.y) / 2

    if frame_shape is not None:
        h, w = frame_shape[:2]
        return int(cx * w), int(cy * h)
    return (cx, cy)


class SmoothedValue:
    """
    Exponential moving average for a single scalar (e.g. head x-position).

    Raw landmark output still has small frame-to-frame jitter even from a
    stable point like the nose tip -- enough to visibly shake a character
    that's mapped 1:1 to it. Wrap the value going into your game loop:

        smoother = SmoothedValue(alpha=0.3)
        ...
        smooth_x = smoother.update(raw_x)

    Lower alpha = smoother but laggier. Higher alpha = snappier but more
    jitter. 0.2-0.4 is a good starting range for character steering.
    """

    __slots__ = ("alpha", "_value")

    def __init__(self, alpha=0.3):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0.0, 1.0]")
        self.alpha = alpha
        self._value = None

    def update(self, new_value):
        if self._value is None:
            self._value = new_value
        else:
            self._value = self.alpha * new_value + (1 - self.alpha) * self._value
        return self._value

    def reset(self):
        self._value = None