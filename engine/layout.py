"""
engine/layout.py

Resolution independence. All pixel constants in the games/HUD are written
for a REF_HEIGHT-pixel-tall frame. ui_scale(frame_h) converts them to the
real frame, so a 1080p camera and a 720p camera play the same.

    ui = ui_scale(frame.shape[0])
    radius_px = BASE_RADIUS * ui
"""

REF_HEIGHT = 720

def ui_scale(frame_h):
    return max(0.5, frame_h / REF_HEIGHT)