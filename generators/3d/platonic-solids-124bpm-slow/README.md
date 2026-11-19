# Five Platonic solids · Tight hexagonal grid · Slow loop

A revised slow three-dimensional wireframe animation with the sphere removed and the grid tightened to match the closely spaced hexagon references.

## Sequence

Tetrahedron → cube → octahedron → dodecahedron → icosahedron → directly back to tetrahedron.

The exported video contains two complete cycles of these five shapes.

## Timing

The tempo remains 124 BPM. Each shape occupies one four-beat bar: three beats held, then one beat morphing into the next shape. The next solid lands on the following downbeat.

- Hold per shape: 45/31 seconds, approximately 1.451613 seconds.
- Morph per transition: 15/31 second, approximately 0.483871 second.
- Total time per shape: 60/31 seconds, approximately 1.935484 seconds.
- One five-shape cycle: 300/31 seconds, approximately 9.677419 seconds.
- Complete video: two cycles, ten bars, 40 beats, or exactly 600/31 seconds, approximately 19.354839 seconds.
- Export: 2,400 frames at 124 fps, with 240 frames per shape and 60 frames per morph.

The two-cycle export keeps the existing slow pace while providing more than ten seconds of video. Start on a song downbeat and enable continuous repeat in your player or VJ software. The video contains no audio.

## Spacing and appearance

1080 × 1080 on pure black, with thin rainbow outlines and dimmer rear edges to reveal depth. The rainbow hue varies continuously across the frame.

The center pitch is reduced from 144 to 108 pixels, placing neighboring centers 25% closer together. The grid remains hexagonal, with a row pitch of approximately 93.530744 pixels and a 54-pixel alternating-row offset. The shape circumradius is 54 pixels, and the outlines are 2 pixels wide. There are 149 grid anchors under the boundary-inclusive crop rule.

Neighboring silhouettes remain separated at every point of every morph. The narrowest silhouette clearance is approximately 4.75 pixels, leaving approximately 2.75 pixels after the outline widths. Maximum-intensity compositing prevents overlapping rectangular drawing tiles from erasing a neighboring shape's lines.

## Morph method

The five regular solids retain their exact geometry and approved perspectives. Their centers stay fixed while outgoing and incoming edge networks deform on an interpolated three-dimensional convex surface. Each held shape retains its exact edge topology. The final transition deforms the icosahedron directly into the tetrahedron.

## Reproduce

Requires Python 3, NumPy, Pillow, and FFmpeg on PATH. SciPy is needed only to regenerate `geometry.json` using the included builder.

```sh
python3 -m pip install numpy pillow scipy
python3 render_animation.py --preview --render
```

Files included: `build_geometry.py`, `geometry.json`, `render_animation.py`, and `animation_spec.json`.

The inline animation preview follows the browser/display refresh rate. The downloadable video retains 124 fps.
