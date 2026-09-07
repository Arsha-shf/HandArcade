import random
import time

import cv2

from engine.camera import show
from engine.tracking import get_fingertip_position

from .hud import draw_game_over, draw_hud
from .spawner import next_spawn_interval, spawn_fruit

WINDOW_NAME = "HandArcade"

MAX_MISSES = 3
TRAIL_LEN = 8

FLASH_LIFETIME = 0.15
PARTICLE_LIFETIME = 0.45
PARTICLES_PER_SLICE = 10
POPUP_LIFETIME = 0.6
GRAVITY_PX_S2 = 900.0

TRACKER_SCALE = 0.5


def run_fruit_slice(cap, tracker, difficulty=None):
    print("Fruit Slice - press ESC to return to menu, 'q' to quit")

    if difficulty is None:
        difficulty = _select_difficulty(cap, tracker)
        if difficulty == "quit":
            return "quit"
        if difficulty == "menu":
            return "menu"

    fruits = []
    score = 0
    misses = 0
    game_over = False

    start_time = time.time()
    last_frame_time = start_time
    next_spawn_time = start_time + 0.5

    trail = []
    flashes = []
    particles = []
    popups = []

    fps_smoothed = 30.0

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        frame = cv2.flip(frame, 1)
        frame_h, frame_w = frame.shape[:2]

        now = time.time()
        raw_dt = now - last_frame_time
        dt = min(raw_dt, 0.05)
        last_frame_time = now

        if raw_dt > 0:
            fps_smoothed = fps_smoothed * 0.9 + (1.0 / raw_dt) * 0.1

        fingertip = _get_fingertip_fast(frame, tracker)

        if not game_over:
            (fruits, score, misses, game_over, trail,
             next_spawn_time, flashes, particles, popups) = _advance_round(
                dt, now, start_time, frame_w, frame_h, fingertip, trail,
                fruits, score, misses, next_spawn_time,
                flashes, particles, popups, difficulty,
            )
        else:
            flashes = _update_flashes(flashes, dt)
            particles = _update_particles(particles, dt)
            popups = _update_popups(popups, dt)

        for fruit in fruits:
            fruit.draw(frame)

        _draw_trail(frame, trail)
        _draw_particles(frame, particles)
        _draw_flashes(frame, flashes)
        _draw_popups(frame, popups)

        if game_over:
            draw_game_over(frame, score)
        else:
            draw_hud(frame, score, misses, MAX_MISSES, fps=fps_smoothed)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if game_over:
            if key != 255:
                return "menu"
        elif key == 27:
            return "menu"


def _get_fingertip_fast(frame, tracker):
    small = cv2.resize(frame, (0, 0), fx=TRACKER_SCALE, fy=TRACKER_SCALE)
    results = tracker.process(small)
    if not results.multi_hand_landmarks:
        return None
    hand_landmarks = results.multi_hand_landmarks[0]
    tip = get_fingertip_position(hand_landmarks, small.shape)
    if tip is None:
        return None
    return (int(tip[0] / TRACKER_SCALE), int(tip[1] / TRACKER_SCALE))


def _select_difficulty(cap, tracker):
    options = [("1", "easy", "Easy"), ("2", "medium", "Medium"), ("3", "hard", "Hard")]
    while True:
        success, frame = cap.read()
        if not success:
            return "quit"
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        title = "Select Difficulty"
        (tw, th), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        cv2.putText(frame, title, ((w - tw) // 2, h // 2 - 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

        for i, (key, _, label) in enumerate(options):
            line = f"{key}) {label}"
            (lw, lh), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            y = h // 2 - 20 + i * 50
            cv2.putText(frame, line, ((w - lw) // 2, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

        hint = "ESC = menu    q = quit"
        (hw, hh), _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.putText(frame, hint, ((w - hw) // 2, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if key == 27:
            return "menu"
        for k, value, _ in options:
            if key == ord(k):
                return value


def _advance_round(dt, now, start_time, frame_w, frame_h, fingertip, trail,
                    fruits, score, misses, next_spawn_time,
                    flashes, particles, popups, difficulty):
    if fingertip is not None:
        trail.append(fingertip)
        if len(trail) > TRAIL_LEN:
            trail.pop(0)
    else:
        trail = []

    if now >= next_spawn_time:
        fruits.append(spawn_fruit(frame_w, frame_h, difficulty=difficulty))
        elapsed = now - start_time
        next_spawn_time = now + next_spawn_interval(elapsed, difficulty=difficulty)

    for fruit in fruits:
        fruit.update(dt)

        if fruit.sliced or not fruit.alive:
            continue

        sliced_this_frame = False
        slice_point = None
        if len(trail) >= 2:
            (px, py), (cx, cy) = trail[-2], trail[-1]
            if fruit.segment_intersects(px, py, cx, cy):
                sliced_this_frame = True
                slice_point = (cx, cy)
        elif fingertip is not None:
            if fruit.contains_point(*fingertip):
                sliced_this_frame = True
                slice_point = fingertip

        if sliced_this_frame:
            fruit.slice()
            if fruit.is_bomb:
                misses += 1
                flashes.append(_make_flash(slice_point or (fruit.x, fruit.y), bomb=True))
                particles.extend(_make_particles(
                    slice_point or (fruit.x, fruit.y), color=(60, 60, 60)))
            else:
                score += fruit.points
                flashes.append(_make_flash(slice_point or (fruit.x, fruit.y), bomb=False))
                particles.extend(_make_particles(
                    slice_point or (fruit.x, fruit.y),
                    color=getattr(fruit, "juice_color", (0, 200, 0))))
                popups.append(_make_popup(slice_point or (fruit.x, fruit.y), fruit.points))

        if fruit.offscreen_bottom_uncollected() and not fruit.is_bomb:
            fruit.alive = False

    fruits = [f for f in fruits if f.alive]

    flashes = _update_flashes(flashes, dt)
    particles = _update_particles(particles, dt)
    popups = _update_popups(popups, dt)

    game_over = misses >= MAX_MISSES
    return (fruits, score, misses, game_over, trail,
            next_spawn_time, flashes, particles, popups)


def _draw_trail(frame, trail):
    if len(trail) < 2:
        return
    n = len(trail)
    for i in range(1, n):
        alpha = i / n
        thickness = max(1, int(2 + 5 * alpha))
        intensity = int(255 * alpha)
        color = (intensity, intensity, intensity)
        cv2.line(frame, trail[i - 1], trail[i], color, thickness, cv2.LINE_AA)

    tip = trail[-1]
    cv2.circle(frame, tip, 7, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, tip, 12, (255, 255, 255), 2, cv2.LINE_AA)


def _make_flash(pos, bomb=False):
    return {"pos": pos, "ttl": FLASH_LIFETIME, "max_ttl": FLASH_LIFETIME, "bomb": bomb}


def _update_flashes(flashes, dt):
    updated = []
    for f in flashes:
        f["ttl"] -= dt
        if f["ttl"] > 0:
            updated.append(f)
    return updated


def _draw_flashes(frame, flashes):
    for f in flashes:
        alpha = f["ttl"] / f["max_ttl"]
        radius = int(18 + (1 - alpha) * 30)
        base_color = (0, 0, 255) if f["bomb"] else (255, 255, 255)
        color = tuple(int(c * alpha) for c in base_color)
        cv2.circle(frame, f["pos"], radius, color, 3, cv2.LINE_AA)


def _make_particles(pos, color, count=PARTICLES_PER_SLICE):
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * 3.14159)
        speed = random.uniform(80, 260)
        vx = speed * random.uniform(-1, 1)
        vy = -abs(speed * random.uniform(0.3, 1.0))
        particles.append({
            "x": float(pos[0]), "y": float(pos[1]),
            "vx": vx, "vy": vy,
            "ttl": PARTICLE_LIFETIME, "max_ttl": PARTICLE_LIFETIME,
            "radius": random.randint(2, 5),
            "color": color,
        })
    return particles


def _update_particles(particles, dt):
    updated = []
    for p in particles:
        p["ttl"] -= dt
        if p["ttl"] <= 0:
            continue
        p["vy"] += GRAVITY_PX_S2 * dt
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        updated.append(p)
    return updated


def _draw_particles(frame, particles):
    for p in particles:
        alpha = max(0.0, p["ttl"] / p["max_ttl"])
        color = tuple(int(c * alpha) for c in p["color"])
        cv2.circle(frame, (int(p["x"]), int(p["y"])), p["radius"],
                   color, -1, cv2.LINE_AA)


def _make_popup(pos, points):
    return {
        "x": float(pos[0]), "y": float(pos[1]),
        "vy": -60.0,
        "ttl": POPUP_LIFETIME, "max_ttl": POPUP_LIFETIME,
        "text": f"+{points}",
    }


def _update_popups(popups, dt):
    updated = []
    for p in popups:
        p["ttl"] -= dt
        if p["ttl"] <= 0:
            continue
        p["y"] += p["vy"] * dt
        updated.append(p)
    return updated


def _draw_popups(frame, popups):
    for p in popups:
        alpha = max(0.0, p["ttl"] / p["max_ttl"])
        color = (0, int(255 * alpha), int(255 * alpha))
        cv2.putText(frame, p["text"], (int(p["x"]), int(p["y"])),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)