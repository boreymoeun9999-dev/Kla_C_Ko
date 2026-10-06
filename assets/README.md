# Pygame asset pack

This asset pack uses a consistent flat-vector look: friendly rounded shapes,
navy outlines, a restrained palette, and transparent backgrounds where the
asset is intended to float over the game UI.

## Files

| File | Intended use | Source size |
| --- | --- | ---: |
| `png/tiger_face.png` | Tiger character icon | 512 x 512 |
| `png/cow_face.png` | Cow character icon | 512 x 512 |
| `png/tiger_cow_badge.png` | Combined character badge | 640 x 640 |
| `png/board_tile.png` | Repeatable checkerboard cell | 128 x 128 |
| `png/selection_frame.png` | Transparent selection corners | 128 x 128 |
| `png/restart_button.png` | Restart control | 256 x 256 |
| `png/close_button.png` | Close control | 256 x 256 |
| `png/score_badge.png` | Empty score badge | 256 x 256 |
| `sounds/tiger-roar.mp3` | Tiger move sound | — |
| `sounds/cow-moo.mp3` | Cow move sound | — |

The webcam game also uses `models/hand_landmarker.task`, the MediaPipe hand
landmark model bundle.

The character icons, selection frame, buttons, and score badge have transparent
backgrounds. The board tile is an opaque, seamless checkerboard cell; alternate
it with another tile or flip it when drawing the board.

## Pygame example

```python
import pygame

pygame.init()
tiger = pygame.image.load("assets/png/tiger_face.png").convert_alpha()
tiger = pygame.transform.smoothscale(tiger, (80, 80))
screen.blit(tiger, (20, 20))
```

To regenerate the PNGs after editing the artwork, run
`python assets/generate_assets.py`. The generator requires Pillow.
