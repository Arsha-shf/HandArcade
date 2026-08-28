"""
engine/tracking.py

MediaPipe hand-tracking wrapper shared by every HandArcade game.

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

import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Landmark indices we care about (see MediaPipe Hands landmark map)
INDEX_FINGER_TIP = mp_hands.HandLandmark.INDEX_FINGER_TIP
THUMB_TIP = mp_hands.HandLandmark.THUMB_TIP
WRIST = mp_hands.HandLandmark.WRIST
MIDDLE_FINGER_MCP = mp_hands.HandLandmark.MIDDLE_FINGER_MCP

# Fingertip / PIP joint pairs used to decide if a finger is "curled"
_FINGER_TIP_PIP_PAIRS = [
    (mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
    (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
    (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
    (mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP),
]


class HandTracker:
    """Thin wrapper around mp.solutions.hands.Hands with sane defaults."""

    def __init__(
        self,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        static_image_mode=False,
    ):
        self._hands = mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr):
        """
        Run hand detection on a BGR frame (as read by cv2.VideoCapture).
        Returns the raw MediaPipe results object
        (has .multi_hand_landmarks and .multi_handedness).
        """
        rgb = frame_bgr[:, :, ::-1]  # BGR -> RGB without an extra cvtColor call
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        return results

    def draw_landmarks(self, frame_bgr, hand_landmarks):
        """Draw MediaPipe's default landmark + connection overlay onto frame_bgr in place."""
        mp_drawing.draw_landmarks(
            frame_bgr,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style(),
        )

    def close(self):
        self._hands.close()

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

        # A curled finger's tip is close to (or closer than) its own PIP joint,
        # rather than extended well beyond it.
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