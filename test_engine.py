"""
test_engine_live.py

Manual visual test for engine/tracking.py + engine/sprites.py working together.
NOT part of the game app itself — just a sanity check you run locally to see
hand tracking and sprite overlay actually working on your webcam before
opening a PR.

Run: python test_engine_live.py
Press 'q' to quit.
"""

import cv2

from engine.sprites import draw_sprite
from engine.tracking import HandTracker, get_fingertip_position, is_fist_closed

SPRITE_PATH = "assets/apple.png"  # swap for any test PNG you have


def main():
    tracker = HandTracker()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Could not open webcam.")
        return

    print("Move your hand in front of the camera. Press 'q' to quit.")

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        results = tracker.process(frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw MediaPipe's landmark skeleton so you can see raw tracking
                tracker.draw_landmarks(frame, hand_landmarks)

                # Get fingertip position in pixel coords
                tip_x, tip_y = get_fingertip_position(hand_landmarks, frame.shape)

                # Overlay a sprite that follows your fingertip
                draw_sprite(frame, SPRITE_PATH, x=tip_x, y=tip_y, scale=1.0)

                # Show fist detection as text feedback
                fist_status = "FIST" if is_fist_closed(hand_landmarks) else "open"
                cv2.putText(
                    frame, fist_status, (tip_x + 20, tip_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
                )
        else:
            cv2.putText(
                frame, "Show your hand to the camera", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2,
            )

        cv2.imshow("Engine Test - tracking + sprites", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    tracker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()