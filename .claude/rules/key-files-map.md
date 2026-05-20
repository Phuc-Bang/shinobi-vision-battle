# Key Files Map

## Backend (`backend/`)

| File | Role |
|------|------|
| `app.py` | Flask-SocketIO server. Listens for `video_frame`, calls gesture detector and game logic, emits `game_update` back to browser. |
| `gesture_detector.py` | Loads MediaPipe Hand + Pose models. Decodes frames, runs inference, classifies gestures into skill/block/dodge. |
| `game_logic.py` | Pure game state: HP pools, skill cooldowns, Kage Bunshin buff timer, boss Kunai AI, win/lose detection. |
| `hand_landmarker.task` | MediaPipe binary model for 2-hand, 21-point detection. Loaded locally; auto-downloaded if missing. |
| `pose_landmarker.task` | MediaPipe binary model for 33-point body pose detection. Loaded locally; auto-downloaded if missing. |
| `requirements.txt` | Python dependency list. |

## Frontend (`frontend/`)

| File | Role |
|------|------|
| `index.html` | Layout: 60% game canvas + 35% HUD (HP bars, skill icons, battle log). Wires audio elements. |
| `script.js` | Socket.IO client. Receives `game_update`, updates HP bars, cooldown overlays, battle log, draws skeleton overlay on webcam canvas. |
| `style.css` | Dark Naruto aesthetic. Neon orange/green palette, screen-shake animation, cooldown overlay, flash effects. |
| `js/webcamFeed.js` | Accesses webcam via `getUserMedia`, captures frames at ~60 fps, encodes to base64, emits `video_frame`. |
| `js/game2d.js` | 2D canvas renderer. Draws character sprites, background, attack animations. |
| `js/gameEngine.js` | Coordinates game2d.js and character.js; drives the animation loop. |
| `js/character.js` | Character class: position, state machine (idle/attack/hurt/win/lose). |
| `js/sprite.js` | Sprite sheet animator: frame stepping, loop/one-shot modes. |

## Assets (`frontend/assets/`)

| Path | Contents |
|------|---------|
| `images/` | Avatars, skill icons, background art |
| `sprites/` | Character sprite sheets for Naruto and Mizuki |
| `story.txt` | Battle story text displayed in the UI |
