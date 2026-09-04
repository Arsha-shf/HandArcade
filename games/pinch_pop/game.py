import random
import time

import cv2

from engine.audio import play_sound
from engine.camera import show
from engine.tracking import (
    INDEX_FINGER_TIP,
    THUMB_TIP,
    get_fingertip_position,
    get_pinch_distance,
)

from . import hud
from .bubbles import BubbleManager
from .score import Score

WINDOW_NAME = "HandArcade"

ROUND_SECONDS = 60
READY_SECONDS = 3
PINCH_THRESHOLD = 0.06

SOUND_POP = "assets/sounds/pop.wav"
SOUND_BOMB = "assets/sounds/hit.wav"

_FLAVOR_WORDS = {
    "normal": ["Pop!", "Bop!", "Blip!"],
    "fast": ["Zoom!", "Whoosh!", "Zap!"],
    "golden": ["JACKPOT!", "CHA-CHING!", "LUCKY!"],
    "bomb": ["OOPS!", "BOOM!", "YIKES!"],
}


def _popup_for(bubble, gained, multiplier):
    word = random.choice(_FLAVOR_WORDS[bubble.kind])
    if bubble.kind == "bomb":
        return f"{word} {gained}", (80, 80, 255), 1.1
    combo_tag = f" x{multiplier}" if multiplier > 1 else ""
    text = f"{word} +{gained}{combo_tag}"
    if bubble.kind == "golden":
        return text, (0, 215, 255), 1.2
    return text, (255, 255, 255), 0.85


_HAND_COLORS = {"Left": (255, 200, 0), "Right": (255, 0, 220)}
_DEFAULT_HAND_COLOR = (255, 255, 255)


def _hand_color(label):
    return _HAND_COLORS.get(label, _DEFAULT_HAND_COLOR)


def _get_pinch_points(results, frame_shape):
    """
    Thumb/index midpoint + pinch state for EVERY detected hand, not just
    the first -- this is what lets two people (or one person, two hands)
    pop bubbles at the same time. tracker was opened with max_num_hands=2
    in engine/menu.py, so up to two hands come back here.
    """
    if not results.multi_hand_landmarks:
        return []

    handedness_list = results.multi_handedness or []
    points = []
    for i, hand in enumerate(results.multi_hand_landmarks):
        label = (
            handedness_list[i].classification[0].label
            if i < len(handedness_list) else f"hand_{i}"
        )
        thumb = get_fingertip_position(hand, frame_shape, finger=THUMB_TIP)
        index = get_fingertip_position(hand, frame_shape, finger=INDEX_FINGER_TIP)
        point = ((thumb[0] + index[0]) // 2, (thumb[1] + index[1]) // 2)
        pinched = get_pinch_distance(hand) < PINCH_THRESHOLD
        points.append({"label": label, "point": point, "pinched": pinched})
    return points


def run_pinch_pop(cap, tracker):
    print("Pinch Pop - pinch a bubble to pop it. Grab a friend, both hands work! ESC = menu, Q = quit")

    state = "ready"
    score = Score()
    bubble_mgr = BubbleManager()
    popups = []

    ready_start = time.time()
    round_start = None
    last_time = time.time()
    pinch_prev = {}
    score_pulse = 0 

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        now = time.time()
        dt = max(0.0, min(0.1, now - last_time)) 
        last_time = now

        results = tracker.process(frame)
        hand_points = _get_pinch_points(results, frame.shape)

        if state == "ready":
            seconds_left = READY_SECONDS - (now - ready_start)
            hud.draw_ready_countdown(frame, seconds_left)
            if seconds_left <= 0:
                state = "playing"
                round_start = now

        elif state == "playing":
            elapsed = now - round_start
            time_left = max(0.0, ROUND_SECONDS - elapsed)

            bubble_mgr.update(dt, frame.shape[1], frame.shape[0], elapsed)
            hud.update_popups(popups, dt)

            # Each hand pops independently, edge-triggered per hand so
            # holding a pinch doesn't machine-gun through every bubble it
            # touches. If two hands land on the same bubble in the same
            # frame, whichever is processed first wins it -- the loser
            # just finds nothing there anymore.
            for hp in hand_points:
                label, point, pinched = hp["label"], hp["point"], hp["pinched"]
                just_pinched = pinched and not pinch_prev.get(label, False)
                if just_pinched:
                    popped = bubble_mgr.try_pop(*point)
                    if popped is not None:
                        gained, multiplier = score.register_pop(popped.points, popped.kind, now)
                        text, color, scale = _popup_for(popped, gained, multiplier)
                        hud.spawn_popup(popups, text, point[0], point[1],
                                         color=color, scale=scale)
                        score_pulse = 8
                        play_sound(SOUND_BOMB if popped.kind == "bomb" else SOUND_POP)
                pinch_prev[label] = pinched

            bubble_mgr.draw(frame)
            hud.draw_popups(frame, popups)

            for hp in hand_points:
                cursor_color = _hand_color(hp["label"]) if hp["pinched"] else (255, 255, 255)
                radius = 10 if hp["pinched"] else 6
                cv2.circle(frame, hp["point"], radius, cursor_color, 2, cv2.LINE_AA)

            pulse = score_pulse / 8.0 if score_pulse > 0 else 0.0
            score_pulse = max(0, score_pulse - 1)
            hud.draw_hud(frame, score, time_left, pulse)

            if time_left <= 0:
                state = "game_over"

        else:
            hud.update_popups(popups, dt)
            bubble_mgr.draw(frame)
            hud.draw_popups(frame, popups)
            hud.draw_game_over(frame, score)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"
        if state == "game_over" and key == ord("r"):
            state = "ready"
            score = Score()
            bubble_mgr.reset()
            popups.clear()
            ready_start = time.time()
            pinch_prev = {}