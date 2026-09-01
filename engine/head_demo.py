"""
engine/head_demo.py

Quick manual test for engine/head_tracking.py.
Opens the webcam, draws the nose-tip point, and overlays raw vs. smoothed
x-position so you can eyeball how much the smoothing helps before wiring
this into Dodge.

Run from the project root:
    python -m engine.head_demo
"""

import cv2

from engine.head_tracking import (
    HeadTracker,
    SmoothedValue,
    get_head_position,
)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam. Check your camera permissions.")
        return

    print("Head tracking demo running. Press 'q' to quit.")

    smoother = SmoothedValue(alpha=0.3)

    with HeadTracker(max_num_faces=1) as tracker:
        while True:
            success, frame = cap.read()
            if not success:
                print("Failed to read frame from webcam.")
                break

            frame = cv2.flip(frame, 1)
            results = tracker.process(frame)

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]

                raw_x, raw_y = get_head_position(face_landmarks, frame.shape)
                smooth_x = int(smoother.update(raw_x))

                # Raw nose tip in red, smoothed x (at the same y) in green,
                # so you can see how much the green dot shakes less.
                cv2.circle(frame, (raw_x, raw_y), 6, (0, 0, 255), -1)
                cv2.circle(frame, (smooth_x, raw_y), 10, (0, 255, 0), 2)

                label = f"raw_x={raw_x}  smooth_x={smooth_x}"
                cv2.putText(
                    frame,
                    label,
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )
            else:
                smoother.reset()  # avoid a stale value snapping back when the face reappears

            cv2.putText(
                frame,
                "HandArcade head tracking demo - press 'q' to quit",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            cv2.imshow("HandArcade - head tracking demo", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()