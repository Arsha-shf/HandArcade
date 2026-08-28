"""
engine/demo.py

Quick manual test for engine/tracking.py.
Opens the webcam, draws hand landmarks, and prints/overlays what each
helper function reports (fingertip, palm center, fist state, pinch distance).

Run from the project root:
    python -m engine.demo
"""

import cv2

from engine.tracking import (
    HandTracker,
    get_fingertip_position,
    get_palm_center,
    is_fist_closed,
    get_pinch_distance,
)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam. Check your camera permissions.")
        return

    print("Tracking demo running. Press 'q' to quit.")

    with HandTracker(max_num_hands=2) as tracker:
        while True:
            success, frame = cap.read()
            if not success:
                print("Failed to read frame from webcam.")
                break

            frame = cv2.flip(frame, 1)
            results = tracker.process(frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    tracker.draw_landmarks(frame, hand_landmarks)

                    tip = get_fingertip_position(hand_landmarks, frame.shape)
                    palm = get_palm_center(hand_landmarks, frame.shape)
                    fist = is_fist_closed(hand_landmarks)
                    pinch = get_pinch_distance(hand_landmarks)

                    cv2.circle(frame, tip, 8, (0, 255, 0), -1)
                    cv2.circle(frame, palm, 8, (255, 0, 0), -1)

                    label = f"fist={fist}  pinch={pinch:.3f}"
                    cv2.putText(
                        frame,
                        label,
                        (tip[0] + 15, tip[1]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255),
                        2,
                    )

            cv2.putText(
                frame,
                "HandArcade tracking demo - press 'q' to quit",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.imshow("HandArcade - tracking demo", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()