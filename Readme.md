# HandArcade 🖐️🎮

A collection of hand-tracking, webcam-based mini-games built in Python.
Move your hand in front of your camera to slice fruit, dodge obstacles, catch objects, and pop bubbles.

## Games
- **Fruit Slice** — slice falling fruit with your fingertip
- **Dodge** — steer left/right with your palm to avoid obstacles
- **Catch** — move your open palm to catch falling objects
- **Pinch Pop** — pinch your thumb and index finger to pop bubbles

## Tech Stack
- Python 3.10+
- [OpenCV](https://opencv.org/) — camera capture & frame drawing
- [MediaPipe](https://developers.google.com/mediapipe) — hand landmark tracking
- Pillow — sprite/PNG overlay with transparency
- NumPy — math helpers

## Project Structure
```
handarcade/
├── engine/          # shared code: camera, tracking, sprite drawing
├── games/           # one file per game
├── assets/          # PNG sprites, sounds
├── main.py          # launcher / menu
└── requirements.txt
```

## Setup
```bash
git clone https://github.com/YOUR_USERNAME/handarcade.git
cd handarcade
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Status
🚧 Early development — engine and menu scaffolding in progress.