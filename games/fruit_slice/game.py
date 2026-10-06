"""
games/fruit_slice/game.py

Main loop. This is the piece engine/menu.py actually calls.

Contract with engine/menu.py:
    run_fruit_slice(cap, tracker, difficulty=None)
    - difficulty None  -> shows a difficulty select screen first (this is
      what the menu triggers, since it calls run_fruit_slice(cap, tracker)).
    - difficulty "easy" / "medium" / "hard" -> starts straight away.
    - Returns "quit" to exit the whole app, "menu" to go back to the menu.
"""

import math
import random
import time

import cv2

from engine import highscores
from engine import hud as engine_hud
from engine.audio import play_sound
from engine.camera import show, to_tracking_frame
from engine.layout import ui_scale
from engine.select_screen import select_option
from engine.tracking import get_fingertip_position

from .difficulty import DIFFICULTY_SETTINGS, get_difficulty
from .fruit import SLICE_PADDING, warm_up
from .hud import draw_game_over, draw_hud
from .spawner import next_spawn_interval, spawn_burst

WINDOW_NAME = "HandArcade"

TRAIL_LEN = 6                # fingertip positions kept for the swipe trail
MAX_DT = 0.05                # a longer hiccup is treated as 50ms
FPS_SAMPLE_COUNT = 30
GAME_OVER_ANIM_DURATION = 0.5

SOUND_SLICE = "assets/sounds/slice.wav"
SOUND_BOMB = "assets/sounds/hit.wav"

COMBO_BONUS = 5              # points per fruit when 2+ are sliced in one swipe-frame

# slice particle burst (px values @720p)
PARTICLE_LIFETIME = 0.4
PARTICLE_COUNT = 14
PARTICLE_GRAVITY = 500.0

CURSOR_RADIUS = 12
CURSOR_COLOR_IDLE = (255, 255, 255)
CURSOR_COLOR_SLICE = (0, 255, 255)

FLASH_DURATION = 0.15        # red flash when a bomb is sliced
POPUP_LIFETIME = 0.8

DIFFICULTY_OPTIONS = [
    (ord("1"), "1 - EASY", (100, 220, 100), "easy"),
    (ord("2"), "2 - MEDIUM", (0, 200, 230), "medium"),
    (ord("3"), "3 - HARD", (60, 60, 230), "hard"),
]
DIFFICULTY_NOTES = [
    "Swipe your index finger through the fruit. Avoid bombs!",
    "Easy: only bombs cost a life.   Medium / Hard: missed fruit cost a life too.",
]


def _best_key(level):
    return f"fruit_slice_{level}"


def _choose_difficulty(cap):
    options = []
    for key, label, color, value in DIFFICULTY_OPTIONS:
        best = highscores.get_best(_best_key(value))
        options.append((key, f"{label}      best {best}", color, value))
    return select_option(cap, "CHOOSE DIFFICULTY", options, DIFFICULTY_NOTES, WINDOW_NAME)


class _Round:
    """All state for one round of Fruit Slice."""

    def __init__(self, level, frame_w, frame_h, ui):
        self.level = level
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.ui = ui

        self.max_lives = DIFFICULTY_SETTINGS[level]["lives"]
        self.lives = self.max_lives
        self.score = 0
        self.t = 0.0
        self.next_spawn = 0.5

        self.fruits = []
        self.particles = []
        self.popups = []       # [x, y, text, color, life_seconds_left]
        self.trail = []
        self.flash = 0.0
        self.over = False

    def advance(self, dt, fingertip):
        """One frame of gameplay. Returns (sliced_any, bomb_hit)."""
        ui = self.ui
        self.t += dt
        params = get_difficulty(self.t, self.level)

        # --- swipe trail ----------------------------------------------------
        if fingertip is not None:
            self.trail.append(fingertip)
            if len(self.trail) > TRAIL_LEN:
                self.trail.pop(0)
        else:
            self.trail = []

        # --- spawn ----------------------------------------------------------
        if self.t >= self.next_spawn:
            live = sum(1 for f in self.fruits if not f.sliced)
            burst = spawn_burst(self.frame_w, self.frame_h, params, ui, self.t,
                                params["max_simultaneous"] - live)
            if burst:
                self.fruits.extend(burst)
                self.next_spawn = self.t + next_spawn_interval(params, len(burst))
            else:
                self.next_spawn = self.t + 0.1   # screen is full: check again shortly

        # --- physics, misses, slicing ------------------------------------------
        sliced_fruit = []
        bomb_hit = False
        padding = SLICE_PADDING * ui

        for fruit in self.fruits:
            fruit.update(dt)

            if fruit.missed:
                if not fruit.is_bomb and params["miss_costs_life"]:
                    self.lives -= 1
                    self.popups.append([fruit.x, min(max(fruit.y, 60 * ui), self.frame_h - 60 * ui),
                                        "MISS", (80, 80, 255), POPUP_LIFETIME])
                continue
            if fruit.sliced or not fruit.alive:
                continue

            hit = False
            if len(self.trail) >= 2:
                (px, py), (cx, cy) = self.trail[-2], self.trail[-1]
                hit = fruit.segment_intersects(px, py, cx, cy, padding)
            elif fingertip is not None:
                hit = fruit.contains_point(*fingertip, padding)

            if not hit:
                continue

            fruit.slice()
            _spawn_particles(self.particles, (fruit.x, fruit.y), fruit.color, ui)
            if fruit.is_bomb:
                self.lives -= 1
                bomb_hit = True
                self.flash = FLASH_DURATION
                play_sound(SOUND_BOMB)
            else:
                self.score += fruit.points
                sliced_fruit.append(fruit)
                play_sound(SOUND_SLICE)
                self.popups.append([fruit.x, fruit.y - 30 * ui, f"+{fruit.points}",
                                    (255, 255, 255), POPUP_LIFETIME])

        if len(sliced_fruit) >= 2:
            bonus = COMBO_BONUS * len(sliced_fruit)
            self.score += bonus
            mx = sum(f.x for f in sliced_fruit) / len(sliced_fruit)
            my = sum(f.y for f in sliced_fruit) / len(sliced_fruit)
            self.popups.append([mx, my - 70 * ui, f"{len(sliced_fruit)}x COMBO +{bonus}",
                                (0, 215, 255), POPUP_LIFETIME * 1.4])

        self.fruits = [f for f in self.fruits if f.alive]

        for popup in self.popups:
            popup[1] -= 40 * ui * dt
            popup[4] -= dt
        self.popups = [p for p in self.popups if p[4] > 0]

        _update_particles(self.particles, dt, ui)
        self.flash = max(0.0, self.flash - dt)

        if self.lives <= 0:
            self.lives = 0
            self.over = True

        return bool(sliced_fruit), bomb_hit


def _spawn_particles(particles, pos, color, ui, count=PARTICLE_COUNT):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(90, 260) * ui
        particles.append({
            "x": pos[0], "y": pos[1],
            "vx": speed * math.cos(angle),
            "vy": speed * math.sin(angle),
            "life": PARTICLE_LIFETIME,
            "color": color,
        })


def _update_particles(particles, dt, ui):
    for p in particles:
        p["vy"] += PARTICLE_GRAVITY * ui * dt
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["life"] -= dt
    particles[:] = [p for p in particles if p["life"] > 0]


def _draw_particles(frame, particles, ui):
    for p in particles:
        t = p["life"] / PARTICLE_LIFETIME
        radius = max(1, int(5 * ui * t))
        cv2.circle(frame, (int(p["x"]), int(p["y"])), radius, p["color"], -1, cv2.LINE_AA)


def run_fruit_slice(cap, tracker, difficulty=None):
    if difficulty is None:
        difficulty = _choose_difficulty(cap)
        if difficulty in ("menu", "quit", None):
            return difficulty or "quit"
    elif difficulty not in DIFFICULTY_SETTINGS:
        difficulty = "medium"

    print(f"Fruit Slice ({difficulty}) - press ESC to return to menu, 'q' to quit")

    success, first_frame = cap.read()
    if not success:
        print("Failed to read frame from webcam.")
        return "quit"
    frame_h, frame_w = first_frame.shape[:2]
    ui = ui_scale(frame_h)
    warm_up(ui)

    rnd = _Round(difficulty, frame_w, frame_h, ui)
    best = highscores.get_best(_best_key(difficulty))
    over_start = None
    over_extra = None
    show_fps = False
    fps_samples = []
    sliced_this_frame = False

    engine_hud.reset_score_animation()
    last_time = time.perf_counter()

    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to read frame from webcam.")
            return "quit"

        now = time.perf_counter()
        raw_dt = now - last_time
        dt = max(0.001, min(MAX_DT, raw_dt))
        last_time = now

        fps_samples.append(1.0 / max(raw_dt, 1e-3))
        if len(fps_samples) > FPS_SAMPLE_COUNT:
            fps_samples.pop(0)
        avg_fps = sum(fps_samples) / len(fps_samples)

        frame = cv2.flip(frame, 1)
        results = tracker.process(to_tracking_frame(frame))

        fingertip = None
        if results.multi_hand_landmarks:
            fingertip = get_fingertip_position(results.multi_hand_landmarks[0], frame.shape)

        if not rnd.over:
            sliced_this_frame, _bomb = rnd.advance(dt, fingertip)
            if rnd.over:
                over_start = time.perf_counter()
                if highscores.submit(_best_key(difficulty), rnd.score):
                    best = rnd.score
                    over_extra = "NEW BEST!"
                else:
                    over_extra = f"Best: {best}"
        else:
            # let the last halves/particles finish animating
            for fruit in rnd.fruits:
                fruit.update(dt)
            _update_particles(rnd.particles, dt, ui)

        for fruit in rnd.fruits:
            fruit.draw(frame)
        _draw_particles(frame, rnd.particles, ui)

        # swipe trail, faded (older points thinner)
        if len(rnd.trail) >= 2:
            for i in range(1, len(rnd.trail)):
                thickness = max(1, int(6 * ui * i / len(rnd.trail)))
                cv2.line(frame, rnd.trail[i - 1], rnd.trail[i], (255, 255, 255),
                         thickness, cv2.LINE_AA)

        if fingertip is not None:
            color = CURSOR_COLOR_SLICE if sliced_this_frame else CURSOR_COLOR_IDLE
            r = int(CURSOR_RADIUS * ui)
            cv2.circle(frame, fingertip, r, color, -1, cv2.LINE_AA)
            cv2.circle(frame, fingertip, r, (0, 0, 0), max(1, round(2 * ui)), cv2.LINE_AA)

        for x, y, text, color, life in rnd.popups:
            engine_hud.draw_popup(frame, x, y, text, color, scale=0.9,
                                  life=min(1.0, life / POPUP_LIFETIME))

        if rnd.flash > 0:
            # in-place red flash: add red to every pixel
            red = int(150 * rnd.flash / FLASH_DURATION)
            cv2.add(frame, (0, 0, red, 0), dst=frame)

        if rnd.over:
            progress = min(1.0, (time.perf_counter() - over_start) / GAME_OVER_ANIM_DURATION)
            draw_game_over(frame, rnd.score, progress=progress, extra=over_extra)
        else:
            draw_hud(frame, rnd.score, rnd.lives, rnd.max_lives, max(best, rnd.score),
                     difficulty, avg_fps if show_fps else None)

        show(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            return "quit"
        if key == 27:
            return "menu"
        if key == ord("f"):
            show_fps = not show_fps
        if rnd.over and key in (ord(" "), ord("r")):
            rnd = _Round(difficulty, frame_w, frame_h, ui)
            over_start = over_extra = None
            engine_hud.reset_score_animation()
            last_time = time.perf_counter()
        if rnd.over and key == ord("d"):
            new_level = _choose_difficulty(cap)
            if new_level in ("menu", "quit", None):
                return new_level or "quit"
            difficulty = new_level
            best = highscores.get_best(_best_key(difficulty))
            rnd = _Round(difficulty, frame_w, frame_h, ui)
            over_start = over_extra = None
            engine_hud.reset_score_animation()
            last_time = time.perf_counter()