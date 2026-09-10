import random
import time
import cv2
import numpy as np
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
from .effects import FrenzyManager, HandSmoother, HandTracker, PinchTracker, ScreenShake, ShieldStatus
from .score import Score

WINDOW_NAME = "HandArcade"

ROUND_SECONDS = 60
READY_SECONDS = 3
PINCH_ENTER_THRESHOLD = 0.055
PINCH_EXIT_THRESHOLD = 0.075

SOUND_POP = "assets/sounds/pop.wav"
SOUND_BOMB = "assets/sounds/hit.wav"
SOUND_SHIELD = "assets/sounds/shield.wav"

_FLAVOR_WORDS = {
    "normal": ["Pop!", "Bop!", "Blip!"],
    "fast": ["Zoom!", "Whoosh!", "Zap!"],
    "golden": ["JACKPOT!", "CHA-CHING!", "LUCKY!"],
    "bomb": ["OOPS!", "BOOM!", "YIKES!"],
    "chain": ["CHAIN!", "COMBO BLAST!", "LINKED!"],
    "shield": ["SHIELD UP!", "GUARDED!", "PROTECTED!"],
}


def _popup_for(bubble, gained, multiplier):
    word = random.choice(_FLAVOR_WORDS[bubble.kind])
    if bubble.kind == "bomb":
        return f"{word} {gained}", (80, 80, 255), 1.1
    combo_tag = f" x{multiplier}" if multiplier > 1 else ""
    text = f"{word} +{gained}{combo_tag}"
    if bubble.kind == "golden":
        return text, (0, 215, 255), 1.2
    if bubble.kind == "chain":
        return text, (230, 60, 210), 1.1
    if bubble.kind == "shield":
        return text, (210, 170, 90), 1.0
    return text, (255, 255, 255), 0.85


_HAND_COLORS = {"Left": (255, 200, 0), "Right": (255, 0, 220)}
_DEFAULT_HAND_COLOR = (255, 255, 255)


def _hand_color(label):
    return _HAND_COLORS.get(label, _DEFAULT_HAND_COLOR)


def _get_pinch_points(results, frame_shape):
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
        distance = get_pinch_distance(hand)
        points.append({"label": label, "point": point, "distance": distance})
    return points


def _resolve_pop(popped, point, score, shield, frenzy, popups, shake, now):
    if popped.kind == "bomb" and shield.has_charge():
        shield.consume()
        hud.spawn_popup(popups, "SHIELDED!", point[0], point[1],
                         color=(210, 170, 90), scale=1.1)
        play_sound(SOUND_SHIELD)
        return

    gained, multiplier = score.register_pop(popped.points, popped.kind, now)

    if popped.kind != "bomb" and frenzy.is_active and frenzy.score_multiplier > 1:
        bonus = gained * (frenzy.score_multiplier - 1)
        score.total += bonus
        gained += bonus

    if popped.kind == "shield":
        shield.grant()

    text, color, scale = _popup_for(popped, gained, multiplier)
    hud.spawn_popup(popups, text, point[0], point[1], color=color, scale=scale)

    if popped.kind == "bomb":
        shake.trigger(0.55)
        play_sound(SOUND_BOMB)
    else:
        if popped.kind in ("golden", "chain"):
            shake.trigger(0.15)
        play_sound(SOUND_POP)


def _handle_hand_pops(hand_points, pinch_prev, bubble_mgr, score, shield,
                       frenzy, popups, shake, now):
    popped_anything = False
    for hp in hand_points:
        hand_id, point, pinched = hp["id"], hp["point"], hp["pinched"]
        just_pinched = pinched and not pinch_prev.get(hand_id, False)
        if just_pinched:
            for popped in bubble_mgr.try_pop(*point):
                popped_anything = True
                popup_at = (int(popped.x), int(popped.y))
                _resolve_pop(popped, popup_at, score, shield, frenzy, popups, shake, now)
        pinch_prev[hand_id] = pinched
    return popped_anything


def run_pinch_pop(cap, tracker):
    print("Pinch Pop - pinch a bubble to pop it. Grab a friend, both hands work! ESC = menu, Q = quit")

    state = "ready"
    score = Score()
    bubble_mgr = BubbleManager()
    popups = []
    smoother = HandSmoother()
    hand_tracker = HandTracker()
    pinch_tracker = PinchTracker()
    shake = ScreenShake()
    frenzy = FrenzyManager()
    shield = ShieldStatus()

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
        hand_points = hand_tracker.update(hand_points, dt)
        seen_ids = {hp["id"] for hp in hand_points}
        smoother.forget_missing(seen_ids)
        pinch_tracker.forget_missing(seen_ids)
        for hp in hand_points:
            hp["point"] = smoother.smooth(hp["id"], hp["point"])
            hp["pinched"] = pinch_tracker.update(hp["id"], hp["distance"])

        shake.update(dt)

        if state == "ready":
            seconds_left = READY_SECONDS - (now - ready_start)
            hud.draw_ready_countdown(frame, seconds_left)
            if seconds_left <= 0:
                state = "playing"
                round_start = now

        elif state == "playing":
            elapsed = now - round_start
            time_left = max(0.0, ROUND_SECONDS - elapsed)

            frenzy.update(dt)
            bubble_mgr.spawn_rate_multiplier = frenzy.spawn_rate_multiplier()
            if frenzy.just_started:
                hud.spawn_popup(popups, "BUBBLE FRENZY!", frame.shape[1] // 2,
                                 frame.shape[0] // 2, color=(0, 120, 255),
                                 scale=1.4, lifetime=1.2)

            bubble_mgr.update(dt, frame.shape[1], frame.shape[0], elapsed)
            hud.update_popups(popups, dt)

            if _handle_hand_pops(hand_points, pinch_prev, bubble_mgr, score,
                                  shield, frenzy, popups, shake, now):
                score_pulse = 8

            bubble_mgr.draw(frame)
            hud.draw_popups(frame, popups)

            for hp in hand_points:
                cursor_color = _hand_color(hp["label"]) if hp["pinched"] else (255, 255, 255)
                radius = 10 if hp["pinched"] else 6
                cv2.circle(frame, hp["point"], radius, cursor_color, 2, cv2.LINE_AA)

            pulse = score_pulse / 8.0 if score_pulse > 0 else 0.0
            score_pulse = max(0, score_pulse - 1)
            hud.draw_hud(frame, score, time_left, pulse, shield=shield, frenzy=frenzy)

            if time_left <= 0:
                state = "game_over"

        else:
            hud.update_popups(popups, dt)
            bubble_mgr.draw(frame)
            hud.draw_popups(frame, popups)
            hud.draw_game_over(frame, score)

        shake_dx, shake_dy = shake.offset()
        if shake_dx or shake_dy:
            shift = np.float32([[1, 0, shake_dx], [0, 1, shake_dy]])
            frame = cv2.warpAffine(frame, shift, (frame.shape[1], frame.shape[0]),
                                    borderMode=cv2.BORDER_REFLECT)

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
            shield.reset()
            frenzy.reset()
            hand_tracker.reset()
            pinch_tracker.reset()
            smoother.reset()