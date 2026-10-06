import os
import random
import time

import cv2
import numpy as np

from engine import highscores
from engine import hud as engine_hud
from engine.audio import play_sound
from engine.camera import show, to_tracking_frame
from engine.layout import ui_scale
from engine.paths import resolve
from engine.tracking import INDEX_FINGER_TIP, THUMB_TIP, get_fingertip_position

from . import hud
from .bubbles import BubbleManager
from .effects import (
    FrenzyManager,
    HandIdentityTracker,
    HandSmoother,
    PinchTracker,
    ScreenShake,
    ShieldStatus,
    pinch_ratio,
)
from .score import Score

WINDOW_NAME = "HandArcade"
HIGHSCORE_KEY = "pinch_pop"

ROUND_SECONDS = 60
READY_SECONDS = 3
MAX_DT = 0.1

GAME_OVER_ANIM_DURATION = 0.5

SOUND_POP = "assets/sounds/pop.wav"
SOUND_BOMB = "assets/sounds/hit.wav"


def _sound_or(primary, fallback):
    """Use `primary` if the file exists, else `fallback` (so a missing
    shield.wav doesn't make the shield silent / spam the console)."""
    return primary if os.path.exists(resolve(primary)) else fallback


SOUND_SHIELD = _sound_or("assets/sounds/shield.wav", SOUND_POP)

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
        points.append({"label": label, "point": point, "ratio": pinch_ratio(hand, frame_shape)})
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


def _best_combo_line(score):
    return f"Best combo: x{score.best_multiplier()}  ({score.best_combo} in a row)"


def _draw_cursors(frame, hand_points, ui):
    for hp in hand_points:
        color = _hand_color(hp["label"]) if hp["pinched"] else (255, 255, 255)
        radius = int((10 if hp["pinched"] else 6) * ui)
        cv2.circle(frame, hp["point"], radius, color, max(1, round(2 * ui)), cv2.LINE_AA)


def run_pinch_pop(cap, tracker):
    print("Pinch Pop - pinch a bubble to pop it. Grab a friend, both hands work! ESC = menu, Q = quit")

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]
    ui = ui_scale(frame_h)

    state = "ready"
    score = Score()
    bubble_mgr = BubbleManager(ui)
    popups = []
    smoother = HandSmoother()
    hand_tracker = HandIdentityTracker(max_distance=160.0 * ui)
    pinch_tracker = PinchTracker()
    shake = ScreenShake(max_pixels=16 * ui)
    frenzy = FrenzyManager()
    shield = ShieldStatus()
    best = highscores.get_best(HIGHSCORE_KEY)
    over_extra = None

    engine_hud.reset_score_animation()
    ready_start = time.perf_counter()
    round_start = None
    game_over_start = None
    last_time = ready_start
    pinch_prev = {}

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        now = time.perf_counter()
        dt = max(0.0, min(MAX_DT, now - last_time))
        last_time = now

        results = tracker.process(to_tracking_frame(frame))
        hand_points = _get_pinch_points(results, frame.shape)
        hand_points = hand_tracker.update(hand_points, dt)
        seen_ids = {hp["id"] for hp in hand_points}
        smoother.forget_missing(seen_ids)
        pinch_tracker.forget_missing(seen_ids)
        pinch_prev = {k: v for k, v in pinch_prev.items() if k in seen_ids}
        for hp in hand_points:
            hp["point"] = smoother.smooth(hp["id"], hp["point"], dt * 30.0)
            hp["pinched"] = pinch_tracker.update(hp["id"], hp["ratio"])

        shake.update(dt)

        if state == "ready":
            seconds_left = READY_SECONDS - (now - ready_start)
            hud.draw_ready_countdown(frame, seconds_left)
            _draw_cursors(frame, hand_points, ui)
            if seconds_left <= 0:
                state = "playing"
                round_start = now

        elif state == "playing":
            elapsed = now - round_start
            time_left = max(0.0, ROUND_SECONDS - elapsed)
            progress = min(1.0, elapsed / ROUND_SECONDS)

            frenzy.update(dt)
            bubble_mgr.spawn_rate_multiplier = frenzy.spawn_rate_multiplier()
            if frenzy.just_started:
                hud.spawn_popup(popups, "BUBBLE FRENZY!", frame_w // 2, frame_h // 2,
                                color=(0, 120, 255), scale=1.4, lifetime=1.2)

            bubble_mgr.update(dt, frame_w, frame_h, elapsed, progress)
            hud.update_popups(popups, dt, ui)

            _handle_hand_pops(hand_points, pinch_prev, bubble_mgr, score,
                              shield, frenzy, popups, shake, now)

            bubble_mgr.draw(frame)
            hud.draw_popups(frame, popups)
            _draw_cursors(frame, hand_points, ui)

            hud.draw_hud(frame, score, time_left, now, max(best, score.total),
                         shield=shield, frenzy=frenzy)

            if time_left <= 0:
                state = "game_over"
                game_over_start = now
                if highscores.submit(HIGHSCORE_KEY, score.total):
                    best = score.total
                    top = "NEW BEST!"
                else:
                    top = f"Best: {best}"
                bomb_line = ("Didn't touch a single bomb. Show-off." if score.bombs_hit == 0
                             else f"Bombs popped: {score.bombs_hit} (ouch)")
                over_extra = [top, bomb_line]

        else:
            hud.update_popups(popups, dt, ui)
            bubble_mgr.draw(frame)
            hud.draw_popups(frame, popups)
            elapsed = now - game_over_start
            progress = min(1.0, elapsed / GAME_OVER_ANIM_DURATION)
            hud.draw_game_over(frame, score, _best_combo_line(score), progress, over_extra)

        shake_dx, shake_dy = shake.offset()
        if shake_dx or shake_dy:
            shift = np.float32([[1, 0, shake_dx], [0, 1, shake_dy]])
            frame = cv2.warpAffine(frame, shift, (frame_w, frame_h),
                                   borderMode=cv2.BORDER_REFLECT)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            return "menu"
        if key == ord("q"):
            return "quit"
        if state == "game_over" and key in (ord("r"), ord(" ")):
            state = "ready"
            score = Score()
            bubble_mgr.reset()
            popups.clear()
            ready_start = time.perf_counter()
            last_time = ready_start
            game_over_start = None
            over_extra = None
            pinch_prev = {}
            shield.reset()
            frenzy.reset()
            shake.reset()
            hand_tracker.reset()
            pinch_tracker.reset()
            smoother.reset()
            engine_hud.reset_score_animation()