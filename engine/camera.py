"""
engine/camera.py

Camera setup + display for HandArcade: opens the webcam at the highest
resolution/FPS it actually supports, keeps capture latency low, and
handles fullscreen display -- all in one place so the menu and every
game get the same behavior without duplicating this logic five times.

Two requirements that fight each other, solved here:
  1. "Full screen, best resolution" -> big frames.
  2. "Very very smooth"            -> MediaPipe inference has to run on
     SMALL frames, or tracking becomes the bottleneck, not the camera.

The fix: capture and DISPLAY at full resolution, but feed the tracker a
downscaled COPY of each frame. MediaPipe's landmark output is already
normalized (0.0-1.0), so converting it back to pixels against the
full-res frame costs nothing -- see engine/tracking.py's
get_palm_center(landmarks, frame.shape) and the equivalents in
engine/head_tracking.py. Nothing in those files needs to change. This
file just gives every game loop the two frames it needs.

Usage in a game loop (see games/catch/game.py for a full example):

    from engine.camera import open_camera, to_tracking_frame, show

    cap = open_camera()                        # once, in menu.py
    ...
    success, frame = cap.read()                # full res, for display + hit-testing
    frame = cv2.flip(frame, 1)
    small = to_tracking_frame(frame)            # small, cheap copy
    results = tracker.process(small)            # fast
    px, py = get_palm_center(hand_landmarks, frame.shape)   # accurate, full-res pixels
    ...
    show(WINDOW_NAME, frame)                    # fullscreen, letterboxed, not stretched
"""

import cv2

TRACKING_SIZE = (640, 360)

DISPLAY_SIZE = (1920, 1080)

_SCREEN_SIZE = None


def _detect_screen_resolution():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        pass

    try:
        import screeninfo
        m = screeninfo.get_monitors()[0]
        return m.width, m.height
    except Exception:
        pass

    print("Could not detect screen resolution (no tkinter/screeninfo available); "
          "falling back to no letterboxing -- install python3-tk or `pip install "
          "screeninfo` if fullscreen still looks stretched.")
    return DISPLAY_SIZE

_CANDIDATE_RESOLUTIONS = [
    (3840, 2160),
    (2560, 1440),
    (1920, 1080),
    (1280, 720),
    (640, 480),
]


def open_camera(index=0, target_fps=60):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return cap

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, target_fps)

    actual_w, actual_h = 640, 480
    for w, h in _CANDIDATE_RESOLUTIONS:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if actual_w >= w and actual_h >= h:
            break

    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"Camera opened at {actual_w}x{actual_h} @ {actual_fps:.0f}fps "
          f"(tracking runs at {TRACKING_SIZE[0]}x{TRACKING_SIZE[1]})")
    return cap


def to_tracking_frame(frame):
    return cv2.resize(frame, TRACKING_SIZE, interpolation=cv2.INTER_LINEAR)


def init_fullscreen_window(window_name):
    global _SCREEN_SIZE
    _SCREEN_SIZE = _detect_screen_resolution()

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, DISPLAY_SIZE[0], DISPLAY_SIZE[1])
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def show(window_name, frame):
    display_w, display_h = DISPLAY_SIZE
    frame_h, frame_w = frame.shape[:2]

    scale = max(display_w / frame_w, display_h / frame_h)
    new_w, new_h = max(1, int(frame_w * scale)), max(1, int(frame_h * scale))
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    x0 = max(0, (new_w - display_w) // 2)
    y0 = max(0, (new_h - display_h) // 2)
    canvas = resized[y0:y0 + display_h, x0:x0 + display_w]

    screen_w, screen_h = _SCREEN_SIZE if _SCREEN_SIZE is not None else DISPLAY_SIZE

    if (screen_w, screen_h) != (display_w, display_h):
        fit_scale = min(screen_w / display_w, screen_h / display_h)
        fit_w = max(1, int(display_w * fit_scale))
        fit_h = max(1, int(display_h * fit_scale))
        fitted = cv2.resize(canvas, (fit_w, fit_h), interpolation=cv2.INTER_LINEAR)

        letterboxed = cv2.copyMakeBorder(
            fitted,
            top=(screen_h - fit_h) // 2,
            bottom=screen_h - fit_h - (screen_h - fit_h) // 2,
            left=(screen_w - fit_w) // 2,
            right=screen_w - fit_w - (screen_w - fit_w) // 2,
            borderType=cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )
        canvas = letterboxed

    cv2.imshow(window_name, canvas)