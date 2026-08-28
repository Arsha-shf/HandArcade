"""
HandArcade - entry point / launcher.

Right now this just opens the webcam so you can confirm your setup works.
Next step: plug in engine/tracking.py + a real menu.
"""

import cv2


def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Could not open webcam. Check your camera permissions.")
        return

    print("Webcam opened. Press 'q' to quit.")

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            break

        # Mirror the frame so it feels like a mirror, not a security camera
        frame = cv2.flip(frame, 1)

        cv2.putText(
            frame,
            "HandArcade - press 'q' to quit",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        cv2.imshow("HandArcade", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
