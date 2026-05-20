# Shinobi Vision Battle — CLAUDE.md

## Project Overview

A gesture-controlled 2D fighting game (Naruto vs. Mizuki) using webcam + MediaPipe AI.
- **Backend:** Python Flask + Socket.IO — processes webcam frames and runs game logic.
- **Frontend:** HTML/CSS/JS — 2D canvas battle animation with skeleton overlay.
- **Transport:** Real-time WebSocket (Socket.IO) between browser and Python server.

## Architecture

```
browser (frontend/)
  └─ webcamFeed.js  → sends base64 frames over socket → app.py
  └─ script.js      ← receives game_update events      ← app.py

backend/
  app.py            — Flask-SocketIO server (port 5000)
  gesture_detector.py — MediaPipe Hand + Pose landmarker → gesture classification
  game_logic.py     — HP, cooldowns, boss AI, win/lose conditions
```

## How to Run

### Backend
```bash
cd backend
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python app.py          # listens on http://localhost:5000
```

### Frontend
```bash
cd frontend
python -m http.server 8000
# open http://localhost:8000 in browser
```
Or use VS Code Live Server extension.

## Key Files

| File | Purpose |
|------|---------|
| `backend/app.py` | Socket.IO server; handles `video_frame` and emits `game_update` |
| `backend/gesture_detector.py` | MediaPipe Hand + Pose → classifies 5 gestures |
| `backend/game_logic.py` | HP, skill cooldowns, boss Kunai AI, game-over logic |
| `frontend/js/game2d.js` | 2D canvas rendering and animation |
| `frontend/js/webcamFeed.js` | Captures webcam, sends base64 frames via socket |
| `frontend/script.js` | UI updates, skeleton drawing, socket event handlers |
| `backend/hand_landmarker.task` | MediaPipe model file (hand detection) |
| `backend/pose_landmarker.task` | MediaPipe model file (pose/body detection) |

## Game Mechanics

### Player Skills
| Skill | Gesture | Cooldown | Damage | Notes |
|-------|---------|----------|--------|-------|
| Rasengan | Right arm raised, hand open | 2s | 15 HP | — |
| Rasenshuriken | Both arms raised, both hands open | 10s | 30 HP | 3 uses max |
| Kage Bunshin | Arms crossed at chest | 5s | — | 1.5× damage buff for 5s |

### Defense
- **Block** — both wrists together, raised above head → blocks Kunai
- **Dodge Left/Right** — shoulder tilt > 0.05 → evades attack

### Boss AI (Mizuki)
- Throws Kunai every 2.5–3.5s (10 damage)
- 30% chance to dodge player attacks
- Dynamic dialogue based on remaining HP

### Win/Lose
Either player or bot reaches 0 HP ends the game.

## Dependencies (backend/requirements.txt)

```
flask
flask-socketio
opencv-python
mediapipe
numpy
eventlet
pillow
```

## Frontend Assets

```
frontend/assets/
  images/    — avatars, skill icons, backgrounds
  sprites/   — character sprite sheets
  story.txt  — story content

frontend/js/
  sprite.js      — sprite animation
  character.js   — character class
  gameEngine.js  — core game controller
  game2d.js      — 2D canvas rendering
  webcamFeed.js  — webcam capture + frame sending
```

## Important Notes

- CORS is configured `cors_allowed_origins="*"` on the backend — no browser CORS errors expected.
- MediaPipe models (`*.task`) are loaded locally from `backend/`; if missing, auto-downloaded from Google Cloud.
- Webcam frames are sent as base64 strings; high frame rate (~60 fps) is expected.
- Audio elements are wired in `index.html` but SFX files must be placed in `frontend/assets/`.
