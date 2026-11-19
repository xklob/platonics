# Polygon morph loop

A 33-second animation of rainbow regular-polygon outlines on a fixed hexagonal grid.

## Sequence

Triangle → square → pentagon → hexagon → heptagon → octagon → nonagon → decagon → 11-gon → 12-gon → circle → triangle.

Every shape holds for 2.7 seconds, then snaps smoothly to the next shape over 0.3 seconds (18 frames at 60 fps). All motifs move through the same phase. The final circle-to-triangle transition closes the loop.

## Appearance

- Pure black background and empty polygon interiors.
- A single continuous, stationary rainbow field over the whole frame.
- Fixed hexagonal grid: 216-pixel horizontal pitch, 187.0615-pixel row pitch, and a 108-pixel alternating-row offset at 1080 × 1080.
- 72-pixel circumradius and approximately 2.3-pixel outlines.
- Squares, octagons, and 12-gons have horizontal top edges; the other polygons have a top vertex.

## Render

Requires Python 3, NumPy, Pillow, and FFmpeg on PATH.

```sh
python3 -m pip install numpy pillow
python3 render_animation.py --video polygon-morph-2d.mp4 --size 1080 --fps 60
```

To regenerate inspection frames and geometry validation:

```sh
python3 render_animation.py --preview
```

The MP4 has no audio and is encoded with H.264, a 4:2:0 pixel format, and fast-start metadata for broad playback support. Enable repeat in the video player for continuous looping.

## Geometry

Each outline uses the same 262 perimeter parameters. The parameter set contains all polygon corners and a 240-sample circular mesh, which preserves the exact regular-polygon edges at each held state. Corresponding points interpolate with quintic smootherstep easing.

`animation_spec.json` records the sequence, timing, grid centers, orientation rules, and perimeter parameters. `render_animation.py` is the reproducible renderer. The current version covers only 2D shapes.
