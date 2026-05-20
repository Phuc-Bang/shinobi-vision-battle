# Game Mechanics

## HP System

| Entity | Starting HP |
|--------|------------|
| Player (Naruto) | 100 |
| Boss (Mizuki) | 100 |

Game ends when either reaches 0 HP.

## Player Skills

| Skill | Gesture to Trigger | Cooldown | Damage | Special |
|-------|--------------------|----------|--------|---------|
| **Rasengan** | Right arm raised, right hand open | 2s | 15 HP | — |
| **Rasenshuriken** | Both arms raised, both hands open | 10s | 30 HP | Max 3 uses per match |
| **Kage Bunshin** | Arms crossed at chest level | 5s | 0 HP | Applies 1.5× damage buff for 5s |

## Defense Moves

| Move | Gesture | Effect |
|------|---------|--------|
| **Block** | Both wrists close together, raised above head | Negates incoming Kunai damage |
| **Dodge Left** | Shoulder tilt left (delta > 0.05) | Evades attack |
| **Dodge Right** | Shoulder tilt right (delta > 0.05) | Evades attack |

## Boss AI — Mizuki

- **Attack:** Throws Kunai automatically every **2.5–3.5 seconds** (randomized), dealing **10 damage** if not blocked.
- **Dodge:** 30% chance to dodge any player skill.
- **Dialogue:** Dynamic story messages triggered at HP thresholds (75 / 50 / 25 / 0).

## Gesture Detection Thresholds

Gestures are classified from MediaPipe landmark coordinates:
- Arm "raised" = wrist Y-coordinate above shoulder Y-coordinate.
- "Both hands open" = all fingers extended on both hands.
- "Arms crossed" = left wrist X > right shoulder X AND right wrist X < left shoulder X.
- Shoulder tilt = difference in Y-coordinates of left vs. right shoulder normalized to body height.
