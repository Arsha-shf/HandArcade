"""
engine/menu.py

Game-select screen for HandArcade.

Opens the webcam and HandTracker ONCE here, then shares them with whichever
game is launched, so we don't reopen the camera every time the player
bounces between the menu and a game.

Camera is opened via engine.camera.open_camera(), which grabs the highest
resolution the device actually supports, and the window is fullscreen +
letterboxed via engine.camera.show() -- see engine/camera.py for why
those two are handled together instead of with a plain cv2.imshow().

Controls on the menu:
    1-4     -> launch that game
    q       -> quit the app
    m       -> toggle mute
    -  / =  -> music volume down / up
    [  / ]  -> sfx volume down / up

Contract each game's run_xxx() must follow:
    run_xxx(cap, tracker) -> str | None
        - Runs its own loop, reading frames from `cap` and using `tracker`.
        - Return "quit" to exit the whole app.
        - Return anything else (e.g. "menu" or None) to go back to the menu.
        - Should display via engine.camera.show(WINDOW_NAME, frame), not
          cv2.imshow directly, or it won't get the fullscreen/letterbox
          treatment set up here.
"""

import cv2

from engine.audio import (
    get_music_volume,
    get_sfx_volume,
    init_audio,
    is_muted,
    play_music,
    set_music_volume,
    set_sfx_volume,
    toggle_mute,
)
from engine.camera import init_fullscreen_window, open_camera, show
from engine.tracking import HandTracker
from engine.transitions import fade_in, fade_out
from games.catch import run_catch
from games.dodge import run_dodge
from games.fruit_slice import run_fruit_slice
from games.pinch_pop import run_pinch_pop

# Ordered so list index + 1 == the number key that launches it (1-4)
GAMES = [
    ("Fruit Slice", run_fruit_slice),
    ("Dodge", run_dodge),
    ("Catch", run_catch),
    ("Pinch Pop", run_pinch_pop),
]

WINDOW_NAME = "HandArcade"
ARCADE_MUSIC = "assets/music/arcade_theme.mp3"

VOLUME_STEP = 0.05


def _draw_menu(frame):
    cv2.putText(frame, "HandArcade", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(frame, "Press a number to play  -  'q' to quit", (20, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    start_y = 150
    line_height = 45
    for i, (name, _) in enumerate(GAMES):
        y = start_y + i * line_height
        cv2.putText(frame, f"{i + 1}. {name}", (40, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

    _draw_audio_controls(frame)


def _draw_audio_controls(frame):
    h, w = frame.shape[:2]

    mute_text = "MUTED (m to unmute)" if is_muted() else "Sound ON (m to mute)"
    mute_color = (0, 0, 255) if is_muted() else (0, 220, 0)
    cv2.putText(frame, mute_text, (20, h - 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, mute_color, 1, cv2.LINE_AA)

    music_pct = int(round(get_music_volume() * 100))
    sfx_pct = int(round(get_sfx_volume() * 100))

    cv2.putText(frame, f"Music: {music_pct:3d}%   ( - / = )", (20, h - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(frame, f"SFX:   {sfx_pct:3d}%   ( [ / ] )", (20, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)

    _draw_volume_bar(frame, 220, h - 68, music_pct)
    _draw_volume_bar(frame, 220, h - 38, sfx_pct)


def _draw_volume_bar(frame, x, y, pct, width=100, height=12):
    cv2.rectangle(frame, (x, y), (x + width, y + height), (80, 80, 80), 1)
    fill_w = int(width * max(0, min(100, pct)) / 100)
    if fill_w > 0:
        cv2.rectangle(frame, (x, y), (x + fill_w, y + height), (0, 200, 255), -1)


def _handle_audio_key(key):
    """Returns True if the key was an audio control and was handled."""
    if key == ord("m"):
        toggle_mute()
        return True
    if key == ord("-"):
        set_music_volume(get_music_volume() - VOLUME_STEP)
        return True
    if key == ord("="):
        set_music_volume(get_music_volume() + VOLUME_STEP)
        return True
    if key == ord("["):
        set_sfx_volume(get_sfx_volume() - VOLUME_STEP)
        return True
    if key == ord("]"):
        set_sfx_volume(get_sfx_volume() + VOLUME_STEP)
        return True
    return False


def _show_menu_loop(cap):
    """
    Display the menu until the player picks a game (1-4) or quits ('q').
    Returns an int 0-3 (index into GAMES) or the string "quit".
    """
    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        _draw_menu(frame)
        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if key in (ord("1"), ord("2"), ord("3"), ord("4")):
            return int(chr(key)) - 1
        _handle_audio_key(key)


def run_menu():
    """Entry point: loop between the menu and games until the user quits."""
    cap = open_camera()
    if not cap.isOpened():
        print("Could not open webcam. Check your camera permissions.")
        return

    init_fullscreen_window(WINDOW_NAME)
    init_audio()
    play_music(ARCADE_MUSIC)

    print("HandArcade menu running. Press 1-4 to play, 'q' to quit.")

    with HandTracker(max_num_hands=2) as tracker:
        try:
            while True:
                choice = _show_menu_loop(cap)
                if choice == "quit":
                    break

                name, run_game = GAMES[choice]
                print(f"Launching {name}...")

                fade_out(cap, WINDOW_NAME)
                result = run_game(cap, tracker)
                fade_in(cap, WINDOW_NAME)

                if result == "quit":
                    break
                # any other return value (e.g. "menu"/None) just loops back
        finally:
            cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    run_menu()