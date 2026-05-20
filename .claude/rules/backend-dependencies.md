# Backend Dependencies

Defined in `backend/requirements.txt`.

## Packages

| Package | Purpose |
|---------|---------|
| `flask` | HTTP server and routing |
| `flask-socketio` | WebSocket layer on top of Flask |
| `opencv-python` | Decode base64 JPEG frames into numpy arrays for MediaPipe |
| `mediapipe` | Google AI: Hand Landmarker + Pose Landmarker inference |
| `numpy` | Array/matrix operations for landmark coordinate math |
| `eventlet` | High-performance async server that powers Socket.IO under Flask |
| `pillow` | Image format conversion utilities |

## Install

```bash
pip install -r backend/requirements.txt
```

## Python Version

Requires **Python 3.10 or later** (MediaPipe constraint).

## Virtual Environment

Keep dependencies isolated inside `backend/venv/` (or `.venv/` at project root).
Do not install into the system Python.
