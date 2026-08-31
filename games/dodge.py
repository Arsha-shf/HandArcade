"""
games/dodge.py

Stub for the Dodge game.

Contract with engine/menu.py:
    run_dodge(cap, tracker) is called with the already-open cv2.VideoCapture
    and HandTracker (opened once in the menu, shared across games).
    - Run your own loop reading frames from `cap`.
    - Return "quit" to exit the whole app.
    - Return "menu" (or anything else) to go back to the menu screen.

Replace the body below with the real game logic.
"""

import cv2

WINDOW_NAME = "HandArcade"


def run_dodge(cap, tracker):
    print("Dodge - press ESC to return to menu, 'q' to quit")

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        results = tracker.process(frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                tracker.draw_landmarks(frame, hand_landmarks)

        cv2.putText(frame, "Dodge (stub)", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, "ESC = menu    q = quit", (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            return "menu"
        if key == ord("q"):
            return "quit"