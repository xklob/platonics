# Triangle to hexagon · 124 BPM · Fast loops

Two faster versions of the dense rainbow polygon loop, timed for a 124 BPM song.

The sequence is triangle → square → pentagon → hexagon → directly back to triangle. All shapes morph together while their centers stay on the same hexagonal grid.

## Timing and exports

| Version | Shape changes per song beat | Full cycle | Morph time | Frame rate | Frames per cycle |
| --- | ---: | --- | ---: | ---: | ---: |
| 2× | 2 (eighth notes) | 2 beats = 30/31 s ≈ 0.967742 s | 0.06 s | 124 fps | 120 |
| 4× | 4 (sixteenth notes) | 1 beat = 15/31 s ≈ 0.483871 s | 0.03 s | 248 fps | 120 |

The underlying song tempo remains 124 BPM. Each new shape lands on its beat subdivision; the morph occupies the final part of the preceding subdivision. Both the hold and morph durations are divided by the pace multiplier.

The frame rate increases in proportion to the pace, retaining the original 30 frames per shape step and the same temporal samples through every morph. The exports are rendered directly from the geometry at their target frame rates. Their durations match the stated fractions exactly in the video timebase.

## Appearance

- 1080 × 1080, with a pure black background and empty interiors.
- Thin full-rainbow outlines with a continuous stationary diagonal hue gradient.
- Fixed hexagonal grid: 144-pixel horizontal pitch, 72-pixel alternate-row offset.
- Shape circumradius: 54 pixels. Stroke width: 2.3 pixels.
- Square edges aligned horizontally and vertically.
- Quintic easing during each short morph.

## Playback

Play each MP4 at its native speed. Start on a song downbeat and enable continuous repeat in your player or VJ software. In a 4/4 bar, the 2× clip repeats twice and the 4× clip repeats four times. The clips contain no audio.

An inline preview runs at the display/browser refresh rate. The downloadable videos retain their specified higher frame rates.

## Reproduce

Requires Python 3, NumPy, Pillow, and FFmpeg on PATH.

```sh
python3 -m pip install numpy pillow
python3 2x/render_animation.py --video triangle-to-hexagon-124bpm-2x.mp4 --size 1080 --fps 124
python3 4x/render_animation.py --video triangle-to-hexagon-124bpm-4x.mp4 --size 1080 --fps 248
```

Each variant's `animation_spec.json` records its exact timing, grid, colors, and geometry. Earlier versions are separate files.
