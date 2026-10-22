# HandArcade

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Platforms: Windows | macOS](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS-lightgrey)

Four arcade games you play with your hand. HandArcade uses your webcam and
MediaPipe hand tracking, so there is no controller to set up and nothing to hold.

## Games

| Game | You control it with | Goal |
| --- | --- | --- |
| **Fruit Slice** | Index fingertip | Slice flying fruit and avoid the bombs |
| **Dodge** | Palm position and distance from the camera | Survive incoming obstacles, including ones that chase you |
| **Catch** | Open palm, one or both hands | Catch falling objects and miss as few as you can |
| **Pinch Pop** | Thumb and index finger pinch | Pop as many bubbles as possible in 60 seconds |

Every game saves your best score. Rules and scoring are in the
[game guide](docs/GAMES.md).

## Requirements

- A webcam
- Python 3.10 or newer
- Windows or macOS (both tested). Linux should work but is untested.

## Quick start

```bash
git clone https://github.com/Arsha-shf/HandArcade.git
cd Handarcade

python -m venv venv
venv\Scripts\activate                   # macOS / Linux: source venv/bin/activate
pip install -r requirements-dev.txt

python download_models.py               # one time: downloads the hand-tracking model
python generate_placeholder_sounds.py   # optional: creates simple sound effects
python main.py
```

Pick a game on the menu with `1`-`4` or by clicking it. Menu music is optional:
add `assets/music/arcade_theme.ogg`, `.mp3` or `.wav` to enable it.

## Controls

| Key | Action |
| --- | --- |
| `1`-`4` / click | Start a game (menu) |
| `1` `2` `3` | Choose difficulty (Fruit Slice, Dodge) |
| `SPACE` or `r` | Play again after a game over |
| `d` | Change difficulty after a game over (Fruit Slice, Dodge) |
| `ESC` | Back to the menu |
| `q` | Quit |
| `m` | Mute (menu) |
| `-` `=` / `[` `]` | Music / sound-effect volume (menu) |

The menu also has clickable volume sliders. Fruit Slice shows an FPS counter
with `f`.

For reliable tracking, use even lighting, keep your whole hand in frame about an
arm's length from the camera, and close other apps that use the camera.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `Hand landmark model not found` | Run `python download_models.py`. |
| `Could not open webcam` or a black window | Allow camera access for your terminal or IDE (macOS: System Settings > Privacy & Security > Camera) and close other apps using the camera. To use a different camera, change `open_camera(index=1)` in `engine/menu.py`. |
| No camera under WSL | Webcams are not available in WSL by default. Run Python directly on Windows. |
| No sound or music | Check `pygame` is installed and an audio device exists. Missing files are listed in the console. |
| Hand is lost or jumpy | Improve the lighting and show your whole hand against a plain background. |
| Low frame rate | Remove `(1920, 1080)` from `_CANDIDATE_RESOLUTIONS` in `engine/camera.py`. |
| `pip install mediapipe` fails | MediaPipe only publishes wheels for some Python versions. Use Python 3.11. |

## Documentation

- [Game guide](docs/GAMES.md): rules, scoring and difficulty for each game
- [Development guide](docs/DEVELOPMENT.md): project structure, tuning, adding a
  game, the art pipeline, and building a standalone app

## Acknowledgements

Built with [MediaPipe](https://developers.google.com/mediapipe),
[OpenCV](https://opencv.org/), [pygame](https://www.pygame.org/) and
[NumPy](https://numpy.org/).