# Triangle to hexagon loop

A 12-second rainbow polygon animation on a fixed hexagonal grid.

## Sequence and timing

Triangle → square → pentagon → hexagon → triangle.

The hexagon morphs directly into the triangle to close the loop. Every shape holds for 2.7 seconds, then morphs for 0.3 seconds (18 frame intervals at 60 fps). All shapes animate in sync.

## Appearance

Pure black background, empty polygon interiors, fine rainbow outlines, and one stationary diagonal hue field across the entire frame. The square stays aligned north–south/east–west. Grid centers and spacing stay fixed throughout. At 1080 × 1080, the shapes have a 54-pixel circumradius and 144-pixel horizontal center spacing, with a 72-pixel alternating-row offset. This revision uses 25% smaller shapes and one-third tighter center spacing.

## Reproduce

Requires Python 3, NumPy, Pillow, and FFmpeg on PATH.

```sh
python3 -m pip install numpy pillow
python3 render_animation.py --video triangle-to-hexagon-loop.mp4 --size 1080 --fps 60
```

Run `python3 render_animation.py --preview` for inspection frames and geometry checks. `animation_spec.json` records the exact timing, shapes, grid, and colors.

The MP4 is 1080 × 1080 at 60 fps, H.264, with no audio. Enable repeat in the video player for continuous looping. The renderer uses shared perimeter points and quintic easing to preserve regular polygon endpoints and a continuous loop.
