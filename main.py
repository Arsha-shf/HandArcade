"""
main.py

Entry point for HandArcade. Deliberately empty of logic -- the menu loop,
camera setup, and game dispatch all live in engine/menu.py. If you find
yourself adding a cv2.VideoCapture() or a while-loop here, stop: that
logic belongs in engine/menu.py, not here. Two copies of the same loop
is exactly how the resolution/fullscreen changes silently failed to do
anything last time -- this file was running its own stale copy while
engine/menu.py got edited.
"""

from engine.menu import run_menu

if __name__ == "__main__":
    run_menu()