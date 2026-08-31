"""
engine/menu.py

Game-select screen for HandArcade.

Opens the webcam and HandTracker ONCE here, then shares them with whichever
game is launched, so we don't reopen the camera every time the player
bounces between the menu and a game.

Controls on the menu:
    1-4  -> launch that game
    q    -> quit the app

Contract each game's run_xxx() must follow:
    run_xxx(cap, tracker) -> str | None
        - Runs its own loop, reading frames from `cap` and using `tracker`.
        - Return "quit" to exit the whole app.
        - Return anything else (e.g. "menu" or None) to go back to the menu.
"""

import cv2

from engine.tracking import HandTracker
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
        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if key in (ord("1"), ord("2"), ord("3"), ord("4")):
            return int(chr(key)) - 1


def run_menu():
    """Entry point: loop between the menu and games until the user quits."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam. Check your camera permissions.")
        return

    print("HandArcade menu running. Press 1-4 to play, 'q' to quit.")

    with HandTracker(max_num_hands=2) as tracker:
        try:
            while True:
                choice = _show_menu_loop(cap)
                if choice == "quit":
                    break

                name, run_game = GAMES[choice]
                print(f"Launching {name}...")
                result = run_game(cap, tracker)
                if result == "quit":
                    break
                # any other return value (e.g. "menu"/None) just loops back
        finally:
            cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    run_menu()