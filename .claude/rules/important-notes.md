# Important Notes & Gotchas

## CORS

Backend sets `cors_allowed_origins="*"` in Flask-SocketIO.
No CORS errors are expected between `localhost:8000` (frontend) and `localhost:5000` (backend).
Do not restrict origins without also updating the frontend URL.

## MediaPipe Model Files

- `backend/hand_landmarker.task` and `backend/pose_landmarker.task` must exist locally.
- If either is missing, the detector auto-downloads it from Google Cloud Storage on first run.
- Commit these files or ensure network access is available on first boot.

## Webcam Frame Rate

- `webcamFeed.js` captures and emits at ~60 fps.
- Each frame is base64-encoded JPEG — adjust quality/resolution in `webcamFeed.js` if latency is too high.
- The backend processes frames synchronously; drop frames rather than queue them if the server falls behind.

## Audio

- 7 `<audio>` elements are wired in `index.html` for BGM and SFX (skills, win, lose, hit).
- Sound files are **not included** in the repo — place `.mp3`/`.ogg` files in `frontend/assets/` matching the `src` attributes in `index.html`.
- SFX is triggered in `script.js` by matching keywords in the battle log message.

## Socket Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `video_frame` | browser → server | `{ frame: "<base64 JPEG>" }` |
| `game_update` | server → browser | `{ player_hp, boss_hp, action, cooldowns, landmarks }` |
| `reset_game` | browser → server | `{}` |
| `connect` | server event | resets game state on new connection |

## Known Constraints

- Single-player only (one webcam, one player vs. bot Mizuki).
- Rasenshuriken is limited to 3 uses per match — not configurable from the frontend.
- Gesture detection accuracy degrades in low-light conditions; recommend adequate room lighting.
