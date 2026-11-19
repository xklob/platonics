# Hypercube projection loop

Thin rainbow tesseract wireframes on a fixed, tightly spaced hexagonal grid. The loop moves through the three selected views:

**Classic nested cubes → frontal square depth → octagonal projection → classic nested cubes.**

The video contains two complete cycles. Every view holds for three beats and morphs during the fourth beat, with smooth acceleration and deceleration. The black background and continuous diagonal rainbow remain fixed throughout.

## Render specification

| Setting | Value |
| --- | --- |
| Resolution | 1080 × 1080 |
| Tempo | 124 BPM |
| Frame rate | 124 fps |
| Duration | 360/31 seconds, approximately 11.612903 seconds |
| Frame count | 1,440 |
| Sequence | Three views, repeated twice |
| Timing per view | 180 hold frames + 60 morph frames |
| Musical length | 24 beats / six 4/4 bars |
| Encoding | H.264, CRF 16, YUV 4:2:0, MP4 with fast start |
| Audio | Silent |
| Grid | 108 px pitch; alternate rows offset by 54 px |
| Motif radius | 52 px |
| Outline | 2 px, rendered with 3× antialiasing |

At this tempo each beat is exactly 60 video frames. The video and track timescales preserve the exact duration, so repeated playback stays aligned with 124 BPM.

## Geometry and motion

The same graph of 16 four-dimensional vertices and 32 edges is present in every frame. The animation interpolates the projection matrix, perspective denominator, and individual edge brightness. All edges remain visible.

Each vertex is projected with `xy = (P @ v) / (1 - q @ v)`, then centered and uniformly fitted to the motif radius. Signed coordinate permutations improve correspondence between the selected views without changing their endpoint images. This is a continuous projective morph of the tesseract graph.

The radius is kept fixed at 52 px. With neighboring centers 108 px apart, the geometric bounds retain at least a 4 px gap, leaving at least 2 px between the 2 px strokes. Maximum compositing preserves neighboring lines where raster tiles overlap.

Hue varies continuously with position, `h = ((x + y) / 1080) % 1`, across the full spectrum. There is no temporal color drift, and no color discontinuity at the loop boundary.

## Re-render

Requires Python 3, NumPy, Pillow, and the `ffmpeg` and `ffprobe` executables on your path.

```bash
python3 -m pip install numpy Pillow
python3 build_geometry.py
python3 render_animation.py --preview --render
```

`geometry.json` is included, so rebuilding it is optional. The renderer writes the MP4, the animation specification, and diagnostic previews alongside its source. `--size 540` can produce a smaller preview render; it uses the same output filename, so keep that render in a separate copy of this directory.

## Included source

- `build_geometry.py`: selected projections, vertex correspondence, and geometric validation.
- `geometry.json`: the complete graph, projection parameters, and timing.
- `render_animation.py`: deterministic raster renderer and video export.
- `animation_spec.json`: final playback, layout, color, and encoding parameters.

Validation covers graph topology, finite projections, non-collapsing vertices, fixed grid anchors, all six timed keyframes, exact cycle closure, and the encoded frame count and duration.
