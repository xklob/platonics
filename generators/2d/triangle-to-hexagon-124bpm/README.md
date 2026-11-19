# Triangle to hexagon · 124 BPM

A fast, single-bar loop for music at 124 BPM in 4/4.

## Beat sequence

1. Triangle
2. Square
3. Pentagon
4. Hexagon

The hexagon morphs directly into the triangle on the next downbeat. Each new shape lands on a beat; its morph occupies the final 0.12 seconds before that beat.

- Beat duration: 60 / 124 = 15 / 31 seconds, approximately 0.483871 seconds.
- Hold per shape: approximately 0.363871 seconds.
- Morph per transition: 0.12 seconds.
- One complete bar: 240 / 124 = 60 / 31 seconds, approximately 1.935484 seconds.

## Appearance

Small rainbow outlines on a dense fixed hexagonal grid: 54-pixel circumradius, 144-pixel center spacing, and 72-pixel alternating-row offset at 1080 × 1080. The background and shape interiors are black. All shapes morph in sync, and the rainbow field stays fixed in space.

## Playback and exact timing

The MP4 contains exactly 120 frames at 62 fps: 30 frames per beat and four beats per loop. This frame rate makes the clip duration match 124 BPM exactly. Play at its native speed, start on a downbeat, and enable continuous repeat in the player or VJ software. The clip contains no audio.

## Reproduce

Requires Python 3, NumPy, Pillow, and FFmpeg on PATH.

```sh
python3 -m pip install numpy pillow
python3 render_animation.py --video triangle-to-hexagon-124bpm.mp4 --size 1080 --fps 62
```

`animation_spec.json` records the exact tempo, timing, shapes, grid, and colors. The renderer preserves the polygon endpoints and uses quintic easing for the short transitions.
