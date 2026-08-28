"""
engine/tracking.py

MediaPipe hand-tracking wrapper shared by every HandArcade game.

Migrated to the MediaPipe Tasks API (HandLandmarker), since the legacy
`mp.solutions.hands` API was removed in recent mediapipe releases.
Public interface is unchanged from the old version.

Usage:
    from engine.tracking import HandTracker

    tracker = HandTracker()
    results = tracker.process(frame)  # frame = BGR image from cv2

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            tip = get_fingertip_position(hand_landmarks, frame.shape)
            palm = get_palm_center(hand_landmarks, frame.shape)
            fist = is_fist_closed(hand_landmarks)
            pinch = get_pinch_distance(hand_landmarks)
"""

import math
import os

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# Model file downloaded once via:
#   wget -O engine/models/hand_landmarker.task \
#     https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
_DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "models", "hand_landmarker.task"
)

# Landmark indices (standard 21-point hand topology, unchanged from the
# legacy API's mp_hands.HandLandmark enum values).
WRIST = 0
THUMB_TIP = 4
INDEX_FINGER_MCP = 5
INDEX_FINGER_PIP = 6
INDEX_FINGER_TIP = 8
MIDDLE_FINGER_MCP = 9
MIDDLE_FINGER_PIP = 10
MIDDLE_FINGER_TIP = 12
RING_FINGER_PIP = 14
RING_FINGER_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20

# Fingertip / PIP joint pairs used to decide if a finger is "curled"
_FINGER_TIP_PIP_PAIRS = [
    (INDEX_FINGER_TIP, INDEX_FINGER_PIP),
    (MIDDLE_FINGER_TIP, MIDDLE_FINGER_PIP),
    (RING_FINGER_TIP, RING_FINGER_PIP),
    (PINKY_TIP, PINKY_PIP),
]


class _HandLandmarksProxy:
    """Mimics the old NormalizedLandmarkList: exposes `.landmark` as a list of points."""

    __slots__ = ("landmark",)

    def __init__(self, landmark_list):
        self.landmark = landmark_list


class _HandednessProxy:
    """Mimics the old `multi_handedness[i].classification[0].label/.score` shape."""

    class _Classification:
        __slots__ = ("label", "score")

        def __init__(self, category):
            self.label = category.category_name
            self.score = category.score

    __slots__ = ("classification",)

    def __init__(self, categories):
        self.classification = [self._Classification(c) for c in categories]


class _ResultsProxy:
    """Mimics the old `results` object returned by mp.solutions.hands.Hands.process()."""

    __slots__ = ("multi_hand_landmarks", "multi_handedness")

    def __init__(self, task_result):
        hands = [_HandLandmarksProxy(h) for h in task_result.hand_landmarks]
        handed = [_HandednessProxy(h) for h in task_result.handedness]
        self.multi_hand_landmarks = hands or None
        self.multi_handedness = handed or None


class HandTracker:
    """Thin wrapper around mp.tasks.vision.HandLandmarker with the old Hands()-like interface."""

    def __init__(
        self,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        static_image_mode=False,
        model_path=_DEFAULT_MODEL_PATH,
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Hand landmark model not found at {model_path}. "
                "Download it with:\n"
                "  wget -O engine/models/hand_landmarker.task "
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                "hand_landmarker/float16/1/hand_landmarker.task"
            )

        self._static_image_mode = static_image_mode
        running_mode = (
            mp_vision.RunningMode.IMAGE if static_image_mode else mp_vision.RunningMode.VIDEO
        )

        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=running_mode,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self._frame_count = 0

    def process(self, frame_bgr):
        """
        Run hand detection on a BGR frame (as read by cv2.VideoCapture).
        Returns a proxy object with .multi_hand_landmarks and .multi_handedness,
        matching the old mp.solutions.hands results shape.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        if self._static_image_mode:
            result = self._landmarker.detect(mp_image)
        else:
            self._frame_count += 1  # just needs to be monotonically increasing
            result = self._landmarker.detect_for_video(mp_image, self._frame_count)

        return _ResultsProxy(result)

    def draw_landmarks(self, frame_bgr, hand_landmarks):
        """Draw hand landmark points + connections onto frame_bgr in place."""
        h, w = frame_bgr.shape[:2]
        connections = mp_vision.HandLandmarksConnections.HAND_CONNECTIONS

        for connection in connections:
            start = hand_landmarks.landmark[connection.start]
            end = hand_landmarks.landmark[connection.end]
            x1, y1 = int(start.x * w), int(start.y * h)
            x2, y2 = int(end.x * w), int(end.y * h)
            cv2.line(frame_bgr, (x1, y1), (x2, y2), (255, 255, 255), 2)

        for lm in hand_landmarks.landmark:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame_bgr, (x, y), 4, (0, 220, 0), -1)

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


def get_fingertip_position(hand_landmarks, frame_shape=None, finger=INDEX_FINGER_TIP):
    """
    Return the position of a fingertip (index finger by default).

    If frame_shape is given (e.g. frame.shape from cv2), returns pixel (x, y) ints.
    Otherwise returns normalized (x, y) floats in [0, 1].
    """
    lm = hand_landmarks.landmark[finger]
    if frame_shape is not None:
        return _to_pixel(lm, frame_shape)
    return (lm.x, lm.y)


def get_palm_center(hand_landmarks, frame_shape=None):
    """
    Approximate the palm center as the average of wrist + middle-finger MCP,
    which sits roughly in the middle of the palm.

    Returns pixel (x, y) if frame_shape given, else normalized (x, y).
    """
    wrist = hand_landmarks.landmark[WRIST]
    mcp = hand_landmarks.landmark[MIDDLE_FINGER_MCP]
    cx = (wrist.x + mcp.x) / 2
    cy = (wrist.y + mcp.y) / 2

    if frame_shape is not None:
        h, w = frame_shape[:2]
        return int(cx * w), int(cy * h)
    return (cx, cy)


def is_fist_closed(hand_landmarks, curl_threshold=0.07):
    """
    Return True if the hand looks like a closed fist.

    Heuristic: for each of the four non-thumb fingers, compare the
    distance from the wrist to the fingertip vs. wrist to that finger's
    PIP joint. If the tip is not meaningfully farther from the wrist than
    the PIP joint is, the finger is considered curled. If enough fingers
    (>=3) are curled, we call it a closed fist.
    """
    wrist = hand_landmarks.landmark[WRIST]
    curled_count = 0

    for tip_idx, pip_idx in _FINGER_TIP_PIP_PAIRS:
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]

        dist_wrist_tip = math.hypot(tip.x - wrist.x, tip.y - wrist.y)
        dist_wrist_pip = math.hypot(pip.x - wrist.x, pip.y - wrist.y)

        if dist_wrist_tip <= dist_wrist_pip + curl_threshold:
            curled_count += 1

    return curled_count >= 3


def get_pinch_distance(hand_landmarks):
    """
    Return the normalized Euclidean distance between thumb tip and index
    fingertip. Small values (~<0.05-0.07, tune per resolution/use case)
    mean the fingers are pinched together.
    """
    thumb = hand_landmarks.landmark[THUMB_TIP]
    index = hand_landmarks.landmark[INDEX_FINGER_TIP]
    return math.hypot(thumb.x - index.x, thumb.y - index.y)