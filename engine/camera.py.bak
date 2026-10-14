"""
engine/camera.py

Camera setup + display for HandArcade.

Two requirements that fight each other:
  1. Sharp, fullscreen display.
  2. Smooth: MediaPipe must run on SMALL frames.

Solution: capture and display at full camera resolution, but feed the
tracker a downscaled COPY (same aspect ratio). MediaPipe returns
normalized landmarks (0-1), so converting them with the full-res
frame.shape gives accurate full-res pixels at no extra cost.

Display rule (important): show() scales the frame to FIT the window and
centers it with black bars. It never crops and never stretches. That is
exactly the mapping engine/menu_input.window_to_frame_coords() assumes,
so frame coordinates == what you see, for any camera aspect ratio.

Usage in a game loop:

    cap = open_camera()
    success, frame = cap.read()
    frame = cv2.flip(frame, 1)
    small = to_tracking_frame(frame)
    results = tracker.process(small)
    px, py = get_palm_center(hand_landmarks, frame.shape)
    show(WINDOW_NAME, frame)
"""

import cv2

TRACKING_WIDTH = 640

# Legacy names kept so older imports don't break. Not used by this module.
TRACKING_SIZE = (640, 360)
DISPLAY_SIZE = (1920, 1080)

# Capped at 1080p on purpose: every frame is flipped, drawn on, blended and
# resized in Python. At 1440p/4K that costs more than the tracker does and
# the camera usually drops its FPS at those sizes anyway.
_CANDIDATE_RESOLUTIONS = [
    (1920, 1080),
    (1280, 720),
    (640, 480),
]

_screen_size = None


def _get_screen_size():
    """Fallback only (used when the window size can't be queried). Lazy, so
    tkinter is never imported unless really needed."""
    global _screen_size
    if _screen_size is not None:
        return _screen_size

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        _screen_size = (root.winfo_screenwidth(), root.winfo_screenheight())
        root.destroy()
        return _screen_size
    except Exception:
        pass

    try:
        import screeninfo

        m = screeninfo.get_monitors()[0]
        _screen_size = (m.width, m.height)
        return _screen_size
    except Exception:
        pass

    _screen_size = DISPLAY_SIZE
    return _screen_size


def open_camera(index=0, target_fps=60):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return cap

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    for w, h in _CANDIDATE_RESOLUTIONS:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if actual_w >= w and actual_h >= h:
            break

    # FPS after resolution: some drivers reset FPS when the mode changes.
    cap.set(cv2.CAP_PROP_FPS, target_fps)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Camera opened at {actual_w}x{actual_h} @ {actual_fps:.0f}fps "
          f"(tracking runs at {TRACKING_WIDTH}px wide)")
    return cap


def to_tracking_frame(frame):
    """Downscale for MediaPipe, KEEPING the aspect ratio. (A fixed 640x360
    would squash a 4:3 camera and distort the hand/face shape.)"""
    h, w = frame.shape[:2]
    if w <= TRACKING_WIDTH:
        return frame
    new_h = max(1, round(h * TRACKING_WIDTH / w))
    return cv2.resize(frame, (TRACKING_WIDTH, new_h), interpolation=cv2.INTER_AREA)


def init_fullscreen_window(window_name):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def _target_size(window_name):
    """Actual drawable size of the window (works fullscreen or windowed)."""
    try:
        _, _, w, h = cv2.getWindowImageRect(window_name)
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return _get_screen_size()


def show(window_name, frame):
    """Fit `frame` inside the window (preserve aspect, center, black bars)."""
    target_w, target_h = _target_size(window_name)
    frame_h, frame_w = frame.shape[:2]

    scale = min(target_w / frame_w, target_h / frame_h)
    new_w, new_h = max(1, int(frame_w * scale)), max(1, int(frame_h * scale))

    if (new_w, new_h) != (frame_w, frame_h):
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        frame = cv2.resize(frame, (new_w, new_h), interpolation=interp)

    if (new_w, new_h) != (target_w, target_h):
        top = (target_h - new_h) // 2
        left = (target_w - new_w) // 2
        frame = cv2.copyMakeBorder(
            frame,
            top, target_h - new_h - top,
            left, target_w - new_w - left,
            cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )

    cv2.imshow(window_name, frame)