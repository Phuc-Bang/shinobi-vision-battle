# Project Overview & Architecture

## What This Is

A gesture-controlled 2D fighting game: **Naruto vs. Mizuki**.
Players perform real-life hand/body gestures in front of a webcam to cast skills and defeat the boss.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Computer Vision | Google MediaPipe (Hand + Pose Landmarker) |
| Backend | Python, Flask, Flask-SocketIO |
| Frontend | HTML5 Canvas, Vanilla JS, CSS3 |
| Transport | WebSocket via Socket.IO |

## Data Flow

```
Webcam (browser)
  └─ webcamFeed.js   →  base64 frame  →  app.py (Socket.IO event: video_frame)
                                              │
                                    gesture_detector.py
                                    (MediaPipe inference)
                                              │
                                      game_logic.py
                                    (HP / cooldown / boss AI)
                                              │
  └─ script.js       ←  game_update  ←  app.py (Socket.IO emit)
       │
  2D canvas animation (game2d.js) + skeleton overlay (script.js)
```

## Ports

- **Backend:** `http://localhost:5000`
- **Frontend:** `http://localhost:8000` (or VS Code Live Server)
