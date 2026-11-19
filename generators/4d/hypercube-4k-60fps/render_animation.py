#!/usr/bin/env python3
"""Render a native 3840-square tesseract loop at exactly 60 fps.

The graph remains sixteen vertices and thirty-two edges throughout. Projection
matrices, perspective vectors, and edge intensities vary smoothly; no images or
separate line graphs are crossfaded. The original 124 BPM timeline is fitted to
697 constant-rate frames, giving 11.616667 seconds at approximately 123.96 BPM.
Use --zoom 2 for a centered crop rendered directly at the output resolution.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
GEOMETRY = json.loads((HERE / "geometry.json").read_text())
VERTICES = np.asarray(GEOMETRY["vertices"], dtype=float)
EDGES = np.asarray(GEOMETRY["edges"], dtype=int)
POSES = GEOMETRY["poses"]
NAMES = [p["label"] for p in POSES]
SIZE = 1080
EXPORT_SIZE = 3840
RADIUS = float(GEOMETRY.get("radius", 54.0))
STROKE = 2.0
PITCH = 108.0
ROW_PITCH = PITCH * math.sqrt(3) / 2
ORIGIN = (54.0, 54.0)
ANTIALIAS = 3
BPM = 124
FPS = 60
BEAT_SECONDS = Fraction(60, BPM)
STATE_SECONDS = BEAT_SECONDS * 4
HOLD_SECONDS = BEAT_SECONDS * 3
MORPH_SECONDS = BEAT_SECONDS
LOOP_REPEATS = 2
STEP_COUNT = len(POSES) * LOOP_REPEATS
FRAME_COUNT = 697
CYCLE_DURATION = STATE_SECONDS * len(POSES)
DURATION = CYCLE_DURATION * LOOP_REPEATS
VIDEO_DURATION = Fraction(FRAME_COUNT, FPS)
EFFECTIVE_BPM = Fraction(STEP_COUNT * 4 * 60, 1) / VIDEO_DURATION


def centers(zoom: float = 1.0) -> np.ndarray:
    result = []
    reach = (RADIUS + STROKE) * zoom
    for row in range(-2, math.ceil(SIZE / ROW_PITCH) + 3):
        world_y = ORIGIN[1] + row * ROW_PITCH
        y = (world_y - SIZE / 2) * zoom + SIZE / 2
        for col in range(-2, math.ceil(SIZE / PITCH) + 3):
            world_x = ORIGIN[0] + col * PITCH + (row % 2) * PITCH / 2
            x = (world_x - SIZE / 2) * zoom + SIZE / 2
            if -reach <= x <= SIZE + reach and -reach <= y <= SIZE + reach:
                result.append((x, y))
    return np.asarray(result, dtype=float)


CENTERS = centers()


def smootherstep(t: float) -> float:
    t = float(np.clip(t, 0, 1))
    return float(np.clip(t * t * t * (t * (t * 6 - 15) + 10), 0, 1))


def state_at(seconds: float) -> dict:
    step = float(STATE_SECONDS)
    local = seconds % float(DURATION)
    position = local / step
    nearest = round(position)
    if abs(position - nearest) <= 1e-10:
        step_index = nearest % STEP_COUNT
        elapsed = 0.0
    else:
        step_index = min(STEP_COUNT - 1, int(position))
        elapsed = local - step_index * step
    index = step_index % len(POSES)
    blend = smootherstep((elapsed - float(HOLD_SECONDS)) / float(MORPH_SECONDS))
    return {"index": index, "step_index": step_index,
            "cycle": step_index // len(POSES), "next": (index + 1) % len(POSES),
            "blend": blend, "from": NAMES[index],
            "to": NAMES[(index + 1) % len(POSES)], "seconds": local}


def project_pose(index: int, blend: float = 0.0):
    """Return screen vertices, edge intensities, and perspective denominators.

    Exact browser-portable steps: lerp P/q/intensities; raw=(V@P.T)/(1-V@q);
    subtract the midpoint of raw min/max bounds; normalize max vertex radius.
    Both P rows already use screen coordinates; do not flip Y again.
    """
    blend = float(np.clip(blend, 0, 1))
    a, b = POSES[index], POSES[(index + 1) % len(POSES)]
    matrix = np.asarray(a["P"]) * (1 - blend) + np.asarray(b["P"]) * blend
    perspective = np.asarray(a["q"]) * (1 - blend) + np.asarray(b["q"]) * blend
    brightness = np.asarray(a["edge_intensities"]) * (1 - blend) + np.asarray(b["edge_intensities"]) * blend
    denominator = 1 - VERTICES @ perspective
    raw = (VERTICES @ matrix.T) / denominator[:, None]
    midpoint = (raw.min(axis=0) + raw.max(axis=0)) / 2
    points = raw - midpoint
    points *= RADIUS / np.max(np.linalg.norm(points, axis=1))
    return points, brightness, denominator


def rainbow_field(size: int, zoom: float = 1.0) -> np.ndarray:
    coords = (((np.arange(size, dtype=np.float32) + 0.5) / size) - 0.5) / zoom + 0.5
    hue6 = ((coords[:, None] + coords[None, :]) % 1) * 6
    sector = np.floor(hue6).astype(np.int8)
    fraction = hue6 - sector
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    for k in range(6):
        mask = sector == k
        f = fraction[mask]
        one, zero = np.ones_like(f), np.zeros_like(f)
        values = [(one, f, zero), (1 - f, one, zero), (zero, one, f),
                  (zero, 1 - f, one), (f, zero, one), (one, zero, 1 - f)]
        rgb[mask] = np.column_stack(values[k])
    return np.rint(rgb * 255).astype(np.uint8)


class Renderer:
    def __init__(self, size: int = EXPORT_SIZE, zoom: float = 1.0, antialias: int = ANTIALIAS):
        self.size = size
        self.zoom = zoom
        self.centers = centers(zoom)
        self.antialias = antialias
        self.scale = size / SIZE
        self.raster_scale = self.scale * zoom * antialias
        self.half_tile = math.ceil((RADIUS + STROKE + 2) * self.scale * zoom)
        self.tile_size = self.half_tile * 2 + 1
        self.width = max(1, round(STROKE * self.raster_scale))
        self.gradient16 = rainbow_field(size, zoom).astype(np.uint16)
        self.work16 = np.empty_like(self.gradient16)

    def motif(self, index: int, blend: float) -> Image.Image:
        points, brightness, _ = project_pose(index, blend)
        pixels = points * self.raster_scale + self.half_tile * self.antialias
        mask = Image.new("L", (self.tile_size * self.antialias,) * 2, 0)
        draw = ImageDraw.Draw(mask)
        for i in np.argsort(brightness, kind="stable"):
            a, b = EDGES[i]
            draw.line([tuple(pixels[a]), tuple(pixels[b])],
                      fill=round(float(brightness[i]) * 255), width=self.width)
        return mask.resize((self.tile_size, self.tile_size), Image.Resampling.LANCZOS)

    def frame_state(self, index: int, blend: float) -> Image.Image:
        tile = np.asarray(self.motif(index, blend), dtype=np.uint8)
        extent = self.size
        mask_pixels = np.zeros((extent, extent), dtype=np.uint8)
        for center in self.centers:
            x, y = center * self.scale
            left, top = round(x) - self.half_tile, round(y) - self.half_tile
            x0, y0 = max(0, left), max(0, top)
            x1, y1 = min(extent, left + self.tile_size), min(extent, top + self.tile_size)
            if x1 <= x0 or y1 <= y0:
                continue
            destination = mask_pixels[y0:y1, x0:x1]
            source = tile[y0-top:y1-top, x0-left:x1-left]
            np.maximum(destination, source, out=destination)
        np.multiply(self.gradient16, mask_pixels[:, :, None], out=self.work16)
        self.work16 += 127
        np.floor_divide(self.work16, 255, out=self.work16)
        return Image.fromarray(self.work16.astype(np.uint8))

    def frame(self, seconds: float) -> Image.Image:
        state = state_at(seconds)
        return self.frame_state(state["index"], state["blend"])


def source_time_for_frame(frame_index: int) -> float:
    return frame_index / FRAME_COUNT * float(DURATION)


def suffix(zoom: int) -> str:
    return "" if zoom == 1 else "-2x-zoom"


def spec(size: int = EXPORT_SIZE, zoom: int = 1, output: Path | None = None) -> dict:
    nominal_frames_per_pose = Fraction(FRAME_COUNT, STEP_COUNT)
    return {"title": "Hypercube projections · Native 4K · 60 fps", "version": 1,
            "source_bpm": BPM, "effective_bpm": float(EFFECTIVE_BPM),
            "size": [size, size], "variant": "slow-tight", "centered_zoom": zoom,
            "frame_rate": FPS, "frames_per_loop": FRAME_COUNT,
            "nominal_frames_per_pose": str(nominal_frames_per_pose),
            "nominal_hold_frames": str(nominal_frames_per_pose * Fraction(3, 4)),
            "nominal_morph_frames": str(nominal_frames_per_pose * Fraction(1, 4)),
            "source_beat_seconds": float(BEAT_SECONDS), "beats_per_pose": 4,
            "beat_seconds": float(VIDEO_DURATION / (STEP_COUNT * 4)),
            "hold_beats": 3, "morph_beats": 1,
            "beats_per_loop": 4 * STEP_COUNT, "bars_per_loop": STEP_COUNT,
            "cycles_per_video": LOOP_REPEATS, "poses_per_cycle": len(POSES),
            "steps_per_video": STEP_COUNT,
            "source_cycle_duration_seconds": float(CYCLE_DURATION),
            "cycle_duration_seconds": float(VIDEO_DURATION / LOOP_REPEATS),
            "cycle_duration_fraction": str(VIDEO_DURATION / LOOP_REPEATS),
            "source_state_seconds": float(STATE_SECONDS),
            "source_hold_seconds": float(HOLD_SECONDS),
            "source_morph_seconds": float(MORPH_SECONDS),
            "state_seconds": float(VIDEO_DURATION / STEP_COUNT),
            "hold_seconds": float(VIDEO_DURATION / STEP_COUNT * Fraction(3, 4)),
            "morph_seconds": float(VIDEO_DURATION / STEP_COUNT * Fraction(1, 4)),
            "source_duration_seconds": float(DURATION), "source_duration_fraction": str(DURATION),
            "duration_seconds": float(VIDEO_DURATION), "duration_fraction": str(VIDEO_DURATION),
            "timing_adjustment_percent": float((1 - DURATION / VIDEO_DURATION) * 100),
            "sampling": "source_time = frame_index/697 * source_duration; 697 frames at exact60fps",
            "video": (output or HERE / f"hypercube-4k-60fps{suffix(zoom)}.mp4").name,
            "sequence": [p["id"] for p in POSES], "names": NAMES,
            "loop_target": POSES[0]["id"], "geometry_file": "geometry.json",
            "vertices": len(VERTICES), "edges": len(EDGES), "design_radius": RADIUS,
            "output_radius_px": RADIUS * zoom * size / SIZE,
            "output_stroke_width_px": STROKE * zoom * size / SIZE,
            "antialias": ANTIALIAS, "supersampling_scope": "local motif tile only",
            "render_method": "native vector geometry at output resolution; no video upscaling",
            "grid": {"type": "hexagonal", "design_pitch": PITCH,
                     "output_pitch_px": PITCH * zoom * size / SIZE,
                     "design_row_pitch": ROW_PITCH, "design_origin": ORIGIN,
                     "center_transform": "(world_center-540)*zoom+540",
                     "centers_design_units": centers(zoom).tolist(),
                     "compositing": "clipped per-pixel maximum"},
            "morph": {"geometry": "P/q interpolation on a fixed 4D tesseract graph",
                      "projection": "raw = P*v/(1-q*v); bbox-center; normalize maximum radius",
                      "easing": "clamped quintic smootherstep",
                      "brightness": "interpolate per-edge intensities; every edge remains visible"},
            "color": {"hue": "(((screen_x-540)/zoom+540+(screen_y-540)/zoom+540)/1080)%1", "saturation": 1,
                      "value": 1, "background": "#000000", "temporal_drift": False}}


def validate(zoom: int = 1) -> dict:
    assert VERTICES.shape == (16, 4) and EDGES.shape == (32, 2)
    assert len({tuple(v) for v in VERTICES}) == 16
    degree = np.bincount(EDGES.ravel(), minlength=16)
    assert np.all(degree == 4)
    assert len({tuple(sorted(e)) for e in EDGES}) == 32
    assert all(np.count_nonzero(VERTICES[a] != VERTICES[b]) == 1 for a, b in EDGES)
    assert len(POSES) == 3 and LOOP_REPEATS == 2 and FRAME_COUNT == 697 and FPS == 60
    assert VIDEO_DURATION == Fraction(697, 60) and VIDEO_DURATION >= 10
    renderer = Renderer(360, zoom)
    endpoint_checks = []
    for index in range(len(POSES)):
        assert renderer.frame_state(index, 1).tobytes() == renderer.frame_state((index + 1) % len(POSES), 0).tobytes()
        endpoint_checks.append({"from": NAMES[index], "to": NAMES[(index + 1) % len(POSES)], "pixel_error": 0})
    assert float(DURATION) >= 10
    assert renderer.frame(0).tobytes() == renderer.frame(float(DURATION)).tobytes()
    assert renderer.frame(0).tobytes() == renderer.frame(float(CYCLE_DURATION)).tobytes()
    keyframes = []
    for step_index in range(STEP_COUNT):
        index = step_index % len(POSES)
        frame_index = math.ceil(FRAME_COUNT * step_index / STEP_COUNT)
        state = state_at(source_time_for_frame(frame_index))
        assert state["index"] == index and state["blend"] == 0 and state["step_index"] == step_index
        keyframes.append({"first_held_frame": frame_index, "pose": NAMES[index],
                          "cycle": step_index // len(POSES), "video_seconds": frame_index / FPS})
    return {"vertices": 16, "edges": 32, "vertex_degrees": degree.tolist(),
            "fixed_centers": len(renderer.centers), "centered_zoom": zoom,
            "endpoint_checks": endpoint_checks, "exact_loop_closure": True,
            "duration_seconds": float(VIDEO_DURATION), "frame_rate": FPS,
            "frames_per_loop": FRAME_COUNT, "keyframes": keyframes}


def previews(zoom: int = 1) -> None:
    out = HERE / "previews"
    out.mkdir(parents=True, exist_ok=True)
    renderer = Renderer(360, zoom)
    sheet = Image.new("RGB", (1080, 772), (8, 8, 8))
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(NAMES):
        frame = renderer.frame_state(index, 0)
        frame.save(out / f"{POSES[index]['id']}-pattern{suffix(zoom)}.png")
        x = index * 360
        sheet.paste(frame, (x, 26))
        draw.text((x + 12, 6), name, fill=(220, 220, 220))
        sheet.paste(renderer.frame_state(index, 0.5), (x, 412))
        draw.text((x + 12, 392), f"{name} transition", fill=(220, 220, 220))
    sheet.save(out / f"keyframes-and-morphs-contact-sheet{suffix(zoom)}.png")
    (out / f"validation{suffix(zoom)}.json").write_text(json.dumps(validate(zoom), indent=2) + "\n")


def render_video(size: int = EXPORT_SIZE, zoom: int = 1, output: Path | None = None, threads: int = 4) -> dict:
    renderer = Renderer(size, zoom)
    start = time.perf_counter()
    path = output or HERE / f"hypercube-4k-60fps{suffix(zoom)}.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-f", "rawvideo", "-pixel_format", "rgb24",
               "-video_size", f"{size}x{size}", "-framerate", str(FPS),
               "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "medium",
               "-crf", "16", "-pix_fmt", "yuv420p", "-threads", str(threads),
               "-x264-params", "rc-lookahead=12:sync-lookahead=2:ref=2:bframes=2",
               "-video_track_timescale", str(FPS * 1000),
               "-movie_timescale", str(FPS * 1000), "-movflags", "+faststart", str(path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    held_index, held_data = None, None
    try:
        for frame_index in range(FRAME_COUNT):
            state = state_at(source_time_for_frame(frame_index))
            if state["blend"] <= 0:
                if held_index != state["index"]:
                    held_data = renderer.frame_state(state["index"], 0).tobytes()
                    held_index = state["index"]
                data = held_data
            else:
                data = renderer.frame_state(state["index"], state["blend"]).tobytes()
            assert process.stdin is not None
            process.stdin.write(data)
            if frame_index % 60 == 0:
                print(json.dumps({"frame": frame_index, "total": FRAME_COUNT,
                                  "elapsed_seconds": round(time.perf_counter()-start,1)}), flush=True)
        process.stdin.close()
        if process.wait():
            raise RuntimeError("FFmpeg failed")
    except BaseException as error:
        returncode = process.poll()
        if returncode is None:
            process.kill()
            returncode = process.wait()
        raise RuntimeError(f"Video export failed; FFmpeg exit code {returncode}") from error
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,time_base,duration_ts,start_time", "-of", "json", str(path)]))["streams"][0]
    assert int(probe["nb_frames"]) == FRAME_COUNT
    assert Fraction(probe["avg_frame_rate"]) == FPS
    actual_duration = int(probe["duration_ts"]) * Fraction(probe["time_base"])
    assert actual_duration == VIDEO_DURATION and actual_duration >= 10
    assert probe["width"] == size and probe["height"] == size
    assert float(probe["start_time"]) == 0
    result = {"path": str(path), "frames": FRAME_COUNT, "centered_zoom": zoom,
              "fps": FPS, "duration": str(actual_duration),
              "duration_seconds": float(actual_duration),
              "bytes": path.stat().st_size, "stream": probe}
    (HERE / "previews").mkdir(exist_ok=True)
    (HERE / "previews" / f"encoded-validation{suffix(zoom)}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"video": result, "elapsed_seconds": round(time.perf_counter()-start, 2)}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--size", type=int, default=EXPORT_SIZE)
    parser.add_argument("--zoom", type=int, choices=[1, 2], default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    (HERE / f"animation_spec{suffix(args.zoom)}.json").write_text(json.dumps(spec(args.size, args.zoom, args.output), indent=2) + "\n")
    if args.preview:
        previews(args.zoom)
    if args.render:
        render_video(args.size, args.zoom, args.output, args.threads)


if __name__ == "__main__":
    main()
