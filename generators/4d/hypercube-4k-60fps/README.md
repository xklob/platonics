# Hypercube loops: 4K at 60 fps

Two square video exports of the same rainbow hypercube animation:

- `hypercube-4k-60fps.mp4`: the original tight hexagonal grid.
- `hypercube-4k-60fps-2x-zoom.mp4`: a centered 2× zoom. Each hypercube and the spacing between centers are twice as large, with fewer shapes visible in the frame.

Both versions are rendered directly from the mathematical geometry at **3840 × 3840**, with a constant **60 fps**. They follow the selected sequence **classic nested cubes → frontal square depth → octagonal projection → classic**, repeated twice.

## Appearance

The original 16-vertex, 32-edge graph stays connected throughout the morph. The black background, continuous full-rainbow gradient, relative spacing, and edge brightness follow the original animation. The zoom uses a centered crop of that same scene, including its color field.

Geometry is supersampled locally before composition. The output is generated from the projection parameters in `geometry.json`.

## Timing

The source animation uses one four-beat bar per view at 124 BPM: three beats held, then one beat morphing. Each export contains two complete three-view cycles.

The exact source duration is 360/31 seconds, which is 696.7741935 frames at 60 fps. These constant-frame-rate exports use the nearest whole frame count, **697 frames**, and map the full animation phase across that interval. Their exact duration is **697/60 seconds ≈ 11.616667 seconds**. This adds approximately **3.763 ms** per loop, equivalent to an effective tempo of **123.959828 BPM**. Both versions use identical timing and loop continuously.

## Source

- `geometry.json`: the graph, selected projections, and source timing.
- `build_geometry.py`: reconstructs and validates the projection data.
- `render_animation.py`: the native 4K renderer and encoder.
- The per-export specification and validation files record the resolution, frame count, duration, zoom, and video metadata.

Requires Python 3, NumPy, Pillow, and the `ffmpeg` and `ffprobe` executables on your path.

```bash
python3 -m pip install numpy Pillow
python3 render_animation.py --preview --render --zoom 1 --threads 4
python3 render_animation.py --preview --render --zoom 2 --threads 4
```

The commands write separate videos, specifications, and validation reports. Use `--output PATH` to select another output filename. The supplied geometry is ready to use; `python3 build_geometry.py` can regenerate it if needed.
