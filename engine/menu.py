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
    1-4         -> launch that game
    click card  -> launch that game
    q           -> quit the app
    m / click   -> toggle mute (click the "Sound ON/MUTED" label)
    -  / =      -> music volume down / up
    [  / ]      -> sfx volume down / up
    drag bar    -> set music/sfx volume directly

Contract each game's run_xxx() must follow:
    run_xxx(cap, tracker) -> str | None
        - Runs its own loop, reading frames from `cap` and using `tracker`.
        - Return "quit" to exit the whole app.
        - Return anything else (e.g. "menu" or None) to go back to the menu.
        - Should display via engine.camera.show(WINDOW_NAME, frame), not
          cv2.imshow directly, or it won't get the fullscreen/letterbox
          treatment set up here.

The menu got big enough to split by concern:
    engine/menu_state.py  -- shared MenuState + color palette
    engine/menu_input.py  -- mouse callback + coordinate mapping + hit-testing
    engine/menu_draw.py   -- everything drawn on screen
    engine/menu.py (here) -- game list, keyboard handling, the main loop
"""

import cv2

from engine.audio import (
    get_music_volume,
    get_sfx_volume,
    init_audio,
    play_music,
    set_music_volume,
    set_sfx_volume,
    toggle_mute,
)
from engine.camera import init_fullscreen_window, open_camera, show
from engine.menu_draw import draw_menu
from engine.menu_input import game_at, make_mouse_callback, window_to_frame_coords
from engine.menu_state import MenuState, point_in_rect
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


def _show_menu_loop(cap, state):
    """
    Display the menu until the player picks a game (via key or click) or
    quits ('q'). Returns an int 0-3 (index into GAMES) or the string "quit".
    """
    state.reset_for_new_session()

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        draw_menu(WINDOW_NAME, frame, state, GAMES)
        show(WINDOW_NAME, frame)

        if state.mouse_click_pending:
            state.mouse_click_pending = False
            fx, fy = window_to_frame_coords(WINDOW_NAME, *state.mouse_pos, *state.frame_size)
            if state.mute_rect is not None and point_in_rect(fx, fy, state.mute_rect):
                toggle_mute()
            else:
                idx = game_at(state, fx, fy)
                if idx is not None:
                    return idx

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
    state = MenuState()
    cv2.setMouseCallback(WINDOW_NAME, make_mouse_callback(WINDOW_NAME, state))
    init_audio()
    play_music(ARCADE_MUSIC)

    print("HandArcade menu running. Press 1-4 (or click a card) to play, 'q' to quit.")

    with HandTracker(max_num_hands=2) as tracker:
        try:
            while True:
                choice = _show_menu_loop(cap, state)
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