# Platonic solids to sphere · 124 BPM

Three-dimensional rainbow wireframes morph together on a fixed hexagonal grid.

## Sequence

Tetrahedron (D4) → cube (D6) → octahedron (D8) → dodecahedron (D12) → icosahedron (D20) → sphere → directly back to tetrahedron.

All five Platonic solids are represented with their exact regular geometry. A globe-style wireframe represents the sphere. The tetrahedron, octahedron, and icosahedron use the clearer perspectives developed in the preceding designs. The dodecahedron presents a central pentagon and its surrounding faces.

## Timing

The underlying song tempo is 124 BPM. Each morph finishes on a beat subdivision.

| Version | Shapes per beat | Full six-shape cycle | Morph duration | Video frame rate | Frames per loop |
| --- | ---: | --- | ---: | ---: | ---: |
| 2× | 2 | 3 beats = 45/31 s ≈ 1.451613 s | 0.06 s | 124 fps | 180 |
| 4× | 4 | 1.5 beats = 45/62 s ≈ 0.725806 s | 0.03 s | 248 fps | 180 |

There are 30 frames per shape step in both exports. Frame rates increase proportionally to the pace, preserving the same temporal sampling through each morph. Both the MP4 movie and video-track timebases preserve the exact rational loop durations.

Start a clip on a song downbeat and enable continuous repeat in your player or VJ software. Each new shape lands on an eighth-note subdivision in the 2× version or a sixteenth-note subdivision in the 4× version. A six-shape sequence spans three beats or one and a half beats respectively. The clips contain no audio.

## Appearance

- 1080 × 1080 on pure black.
- Small shapes with a 54-pixel circumradius on 72 fixed hexagonal-grid anchors.
- Horizontal center pitch 144 pixels; alternate rows offset by 72 pixels.
- Thin 2-pixel outlines with full-rainbow hue changing continuously across the image.
- Rear edges dimmed to reveal depth, with brighter visible faces and silhouette edges.
- Three-times supersampling during rendering for clean lines and curves.

## Morph method

The animation uses actual three-dimensional coordinates. Every solid is centered and normalized to a circumradius of 1 before projection. For a direction u, each solid's convex gauge is the maximum normalized face-plane dot product; the unit sphere's gauge is 1. A transition linearly interpolates these gauges and projects the corresponding radial surface points into the fixed view.

Outgoing and incoming edge sets both deform on that evolving surface, with their visibility blended during the transition. This handles different edge counts while retaining the exact original edge topology at each held shape. Rear-edge brightness comes from the surface normal's orientation toward the camera.

## Files

- `geometry.json`: all six shapes, exact faces and edges, orientations, and sampled line directions.
- `build_geometry.py`: regenerates and validates the geometry.
- `render_animation.py`: creates previews, verifies the animation, and exports either or both MP4s.
- `animation_spec.json`: geometry, timing, rendering, and layout settings.

## Reproduce

Requires Python 3, NumPy, Pillow, and FFmpeg on PATH. SciPy is needed only to regenerate the geometry.

```sh
python3 -m pip install numpy pillow scipy
python3 render_animation.py --preview --render --speed both
```

Use `--speed 2` or `--speed 4` to render one variant. The included geometry payload lets the renderer run without rebuilding the models.

The inline animation preview follows the browser/display refresh rate. The downloadable videos retain the specified higher frame rates.
