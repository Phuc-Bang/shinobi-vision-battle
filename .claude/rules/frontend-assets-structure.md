# Frontend Assets & Structure

## Directory Tree

```
frontend/
├── index.html          ← entry point
├── script.js           ← socket client + UI + skeleton drawing
├── style.css           ← dark Naruto theme
│
├── js/
│   ├── webcamFeed.js   ← getUserMedia → base64 → socket emit
│   ├── game2d.js       ← canvas 2D renderer
│   ├── gameEngine.js   ← animation loop controller
│   ├── character.js    ← character state machine
│   └── sprite.js       ← sprite sheet frame stepper
│
└── assets/
    ├── images/         ← avatars, skill icons, backgrounds
    ├── sprites/        ← Naruto & Mizuki sprite sheets
    └── story.txt       ← battle story text
```

## Layout (index.html)

```
┌──────────────────────────────┬─────────────────┐
│  Game Canvas (2D battle)     │  SHINOBI BATTLE  │
│  [16:9, fills left 60%]      │                  │
│                              │  Naruto HP ████  │
│  ┌──────────────┐            │  Mizuki HP ████  │
│  │ Webcam feed  │            │                  │
│  │ + skeleton   │            │  [Skill Icons]   │
│  └──────────────┘            │                  │
│  [Story] [Reset]             │  Battle Log      │
│  Defense Guide               │  (scrollable)    │
└──────────────────────────────┴─────────────────┘
```

## Visual Style (style.css)

| Element | Value |
|---------|-------|
| Background | `#1A1A1A` (near black) |
| Primary / Orange | `#FF9900` |
| Player HP bar | `#39FF14` (lime neon) |
| Enemy HP bar | `#FF003C` (crimson) |
| Body font | "Poppins" |
| Title font | "Press Start 2P" |
| Animations | screen-shake, flash, cooldown overlay |

## Skeleton Overlay

Drawn on a `<canvas>` layered over the webcam `<video>`:
- **Pose connections** — neon green, 4px, glow shadow
- **Hand connections** — orange, 3px, glow shadow
- **Joints** — filled circles at each landmark point
