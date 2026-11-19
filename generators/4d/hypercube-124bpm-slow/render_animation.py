#!/usr/bin/env python3
"""Render a tesseract morphing through three connected 4D-to-2D projections.

The graph remains sixteen vertices and thirty-two edges throughout. Projection
matrices, perspective vectors, and edge intensities vary smoothly; no images or
separate line graphs are crossfaded. Each pose occupies one bar at 124 BPM.
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
RADIUS = float(GEOMETRY.get("radius", 54.0))
STROKE = 2.0
PITCH = 108.0
ROW_PITCH = PITCH * math.sqrt(3) / 2
ORIGIN = (54.0, 54.0)
ANTIALIAS = 3
BPM = 124
FPS = 124
BEAT_SECONDS = Fraction(60, BPM)
STATE_SECONDS = BEAT_SECONDS * 4
HOLD_SECONDS = BEAT_SECONDS * 3
MORPH_SECONDS = BEAT_SECONDS
FRAMES_PER_STEP = int(STATE_SECONDS * FPS)
LOOP_REPEATS = 2
STEP_COUNT = len(POSES) * LOOP_REPEATS
FRAME_COUNT = STEP_COUNT * FRAMES_PER_STEP
CYCLE_DURATION = STATE_SECONDS * len(POSES)
DURATION = CYCLE_DURATION * LOOP_REPEATS


def centers() -> np.ndarray:
    result = []
    reach = RADIUS + STROKE
    for row in range(-2, math.ceil(SIZE / ROW_PITCH) + 3):
        y = ORIGIN[1] + row * ROW_PITCH
        for col in range(-2, math.ceil(SIZE / PITCH) + 3):
            x = ORIGIN[0] + col * PITCH + (row % 2) * PITCH / 2
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


def rainbow_field(size: int) -> np.ndarray:
    coords = (np.arange(size, dtype=np.float32) + 0.5) / size
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
    def __init__(self, size: int = SIZE, antialias: int = ANTIALIAS):
        self.size = size
        self.antialias = antialias
        self.scale = size / SIZE
        self.raster_scale = self.scale * antialias
        self.half_tile = math.ceil((RADIUS + STROKE + 2) * self.raster_scale)
        self.tile_size = self.half_tile * 2 + 1
        self.width = max(1, round(STROKE * self.raster_scale))
        self.gradient16 = rainbow_field(size).astype(np.uint16)

    def motif(self, index: int, blend: float) -> Image.Image:
        points, brightness, _ = project_pose(index, blend)
        pixels = points * self.raster_scale + self.half_tile
        mask = Image.new("L", (self.tile_size, self.tile_size), 0)
        draw = ImageDraw.Draw(mask)
        for i in np.argsort(brightness, kind="stable"):
            a, b = EDGES[i]
            draw.line([tuple(pixels[a]), tuple(pixels[b])],
                      fill=round(float(brightness[i]) * 255), width=self.width)
        return mask

    def frame_state(self, index: int, blend: float) -> Image.Image:
        tile = np.asarray(self.motif(index, blend), dtype=np.uint8)
        extent = self.size * self.antialias
        mask_pixels = np.zeros((extent, extent), dtype=np.uint8)
        for center in CENTERS:
            x, y = center * self.raster_scale
            left, top = round(x) - self.half_tile, round(y) - self.half_tile
            x0, y0 = max(0, left), max(0, top)
            x1, y1 = min(extent, left + self.tile_size), min(extent, top + self.tile_size)
            if x1 <= x0 or y1 <= y0:
                continue
            destination = mask_pixels[y0:y1, x0:x1]
            source = tile[y0-top:y1-top, x0-left:x1-left]
            np.maximum(destination, source, out=destination)
        mask = Image.fromarray(mask_pixels).resize((self.size, self.size), Image.Resampling.LANCZOS)
        alpha = np.asarray(mask, dtype=np.uint16)
        result = (self.gradient16 * alpha[:, :, None] + 127) // 255
        return Image.fromarray(result.astype(np.uint8))

    def frame(self, seconds: float) -> Image.Image:
        state = state_at(seconds)
        return self.frame_state(state["index"], state["blend"])


def spec() -> dict:
    return {"title": "Hypercube projections · Slow · 124 BPM", "version": 1,
            "bpm": BPM, "size": [SIZE, SIZE], "variant": "slow-tight",
            "frame_rate": FPS, "frames_per_loop": FRAME_COUNT,
            "frames_per_pose": FRAMES_PER_STEP,
            "hold_frames": int(HOLD_SECONDS * FPS), "morph_frames": int(MORPH_SECONDS * FPS),
            "beat_seconds": float(BEAT_SECONDS), "beats_per_pose": 4,
            "hold_beats": 3, "morph_beats": 1,
            "beats_per_loop": 4 * STEP_COUNT, "bars_per_loop": STEP_COUNT,
            "cycles_per_video": LOOP_REPEATS, "poses_per_cycle": len(POSES),
            "steps_per_video": STEP_COUNT,
            "cycle_duration_seconds": float(CYCLE_DURATION),
            "cycle_duration_fraction": str(CYCLE_DURATION),
            "state_seconds": float(STATE_SECONDS), "hold_seconds": float(HOLD_SECONDS),
            "morph_seconds": float(MORPH_SECONDS),
            "duration_seconds": float(DURATION), "duration_fraction": str(DURATION),
            "video": "hypercube-124bpm-slow.mp4",
            "sequence": [p["id"] for p in POSES], "names": NAMES,
            "loop_target": POSES[0]["id"], "geometry_file": "geometry.json",
            "vertices": len(VERTICES), "edges": len(EDGES), "radius": RADIUS,
            "stroke_width": STROKE, "antialias": ANTIALIAS,
            "grid": {"type": "hexagonal", "pitch": PITCH,
                     "row_pitch": ROW_PITCH, "origin": ORIGIN,
                     "odd_row_offset": PITCH / 2, "centers": CENTERS.tolist(),
                     "compositing": "clipped per-pixel maximum"},
            "morph": {"geometry": "P/q interpolation on a fixed 4D tesseract graph",
                      "projection": "raw = P*v/(1-q*v); bbox-center; normalize maximum radius",
                      "easing": "clamped quintic smootherstep",
                      "brightness": "interpolate per-edge intensities; every edge remains visible"},
            "color": {"hue": "((x+y)/1080)%1", "saturation": 1,
                      "value": 1, "background": "#000000", "temporal_drift": False}}


def validate() -> dict:
    assert VERTICES.shape == (16, 4) and EDGES.shape == (32, 2)
    assert len({tuple(v) for v in VERTICES}) == 16
    degree = np.bincount(EDGES.ravel(), minlength=16)
    assert np.all(degree == 4)
    assert len({tuple(sorted(e)) for e in EDGES}) == 32
    assert all(np.count_nonzero(VERTICES[a] != VERTICES[b]) == 1 for a, b in EDGES)
    assert len(POSES) == 3 and LOOP_REPEATS == 2 and FRAME_COUNT == 1440
    assert len(CENTERS) == 149
    renderer = Renderer(360)
    endpoint_checks = []
    minimum_denominator = float("inf")
    minimum_pair_distance = float("inf")
    minimum_edge_length = float("inf")
    minimum_intensity = float("inf")
    for index in range(len(POSES)):
        assert renderer.frame_state(index, 1).tobytes() == renderer.frame_state((index + 1) % len(POSES), 0).tobytes()
        endpoint_checks.append({"from": NAMES[index], "to": NAMES[(index + 1) % len(POSES)], "pixel_error": 0})
        for blend in np.linspace(0, 1, 241):
            points, brightness, denominator = project_pose(index, float(blend))
            assert np.all(np.isfinite(points)) and np.all(denominator > 0)
            assert np.all((brightness > 0) & (brightness <= 1))
            delta = points[:, None] - points[None, :]
            distances = np.linalg.norm(delta, axis=2)
            np.fill_diagonal(distances, np.inf)
            minimum_denominator = min(minimum_denominator, float(denominator.min()))
            minimum_pair_distance = min(minimum_pair_distance, float(distances.min()))
            minimum_edge_length = min(minimum_edge_length, float(np.linalg.norm(points[EDGES[:, 0]] - points[EDGES[:, 1]], axis=1).min()))
            minimum_intensity = min(minimum_intensity, float(brightness.min()))
    assert minimum_pair_distance > 0.01 and minimum_edge_length > 0.01
    assert float(DURATION) >= 10
    assert renderer.frame(0).tobytes() == renderer.frame(float(DURATION)).tobytes()
    assert renderer.frame(0).tobytes() == renderer.frame(float(CYCLE_DURATION)).tobytes()
    keyframes = []
    for step_index in range(STEP_COUNT):
        index = step_index % len(POSES)
        start = STATE_SECONDS * step_index
        state = state_at(float(start))
        hold_end = state_at(float(start + HOLD_SECONDS))
        midpoint = state_at(float(start + HOLD_SECONDS + MORPH_SECONDS / 2))
        assert state["index"] == index and state["blend"] == 0 and state["step_index"] == step_index
        assert hold_end["index"] == index and hold_end["blend"] < 1e-12
        assert midpoint["index"] == index and abs(midpoint["blend"] - 0.5) < 1e-12
        keyframes.append({"frame": step_index * FRAMES_PER_STEP, "pose": NAMES[index],
                          "cycle": step_index // len(POSES), "seconds": float(start)})
    return {"vertices": 16, "edges": 32, "vertex_degrees": degree.tolist(),
            "fixed_centers": len(CENTERS), "minimum_denominator": minimum_denominator,
            "sampled_minimum_vertex_distance_px": minimum_pair_distance,
            "sampled_minimum_edge_length_px": minimum_edge_length,
            "minimum_edge_intensity": minimum_intensity,
            "endpoint_checks": endpoint_checks, "exact_loop_closure": True,
            "duration_seconds": float(DURATION), "frame_rate": FPS,
            "frames_per_loop": FRAME_COUNT, "keyframes": keyframes}


def previews() -> None:
    out = HERE / "previews"
    out.mkdir(parents=True, exist_ok=True)
    renderer = Renderer(360)
    sheet = Image.new("RGB", (1080, 772), (8, 8, 8))
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(NAMES):
        frame = renderer.frame_state(index, 0)
        frame.save(out / f"{POSES[index]['id']}-pattern.png")
        x = index * 360
        sheet.paste(frame, (x, 26))
        draw.text((x + 12, 6), name, fill=(220, 220, 220))
        sheet.paste(renderer.frame_state(index, 0.5), (x, 412))
        draw.text((x + 12, 392), f"{name} transition", fill=(220, 220, 220))
    sheet.save(out / "keyframes-and-morphs-contact-sheet.png")
    (out / "validation.json").write_text(json.dumps(validate(), indent=2) + "\n")


def render_video(size: int = SIZE) -> dict:
    renderer = Renderer(size)
    start = time.perf_counter()
    path = HERE / "hypercube-124bpm-slow.mp4"
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
               "-f", "rawvideo", "-pixel_format", "rgb24",
               "-video_size", f"{size}x{size}", "-framerate", str(FPS),
               "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "medium",
               "-crf", "16", "-pix_fmt", "yuv420p",
               "-video_track_timescale", str(FPS * 1000),
               "-movie_timescale", str(FPS * 1000), "-movflags", "+faststart", str(path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    cache = {}
    try:
        for frame_index in range(FRAME_COUNT):
            state = state_at(frame_index / FPS)
            if state["blend"] <= 0:
                if state["index"] not in cache:
                    cache[state["index"]] = renderer.frame_state(state["index"], 0).tobytes()
                data = cache[state["index"]]
            else:
                data = renderer.frame_state(state["index"], state["blend"]).tobytes()
            assert process.stdin is not None
            process.stdin.write(data)
            if frame_index % FRAMES_PER_STEP == 0:
                print(json.dumps({"frame": frame_index, "total": FRAME_COUNT}), flush=True)
        process.stdin.close()
        if process.wait():
            raise RuntimeError("FFmpeg failed")
    except BaseException:
        process.kill()
        process.wait()
        raise
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,time_base,duration_ts,start_time", "-of", "json", str(path)]))["streams"][0]
    assert int(probe["nb_frames"]) == FRAME_COUNT
    assert Fraction(probe["avg_frame_rate"]) == FPS
    actual_duration = int(probe["duration_ts"]) * Fraction(probe["time_base"])
    assert actual_duration == DURATION and actual_duration >= 10
    assert float(probe["start_time"]) == 0
    result = {"path": str(path), "frames": FRAME_COUNT,
              "fps": FPS, "duration": str(actual_duration),
              "duration_seconds": float(actual_duration),
              "bytes": path.stat().st_size, "stream": probe}
    (HERE / "previews").mkdir(exist_ok=True)
    (HERE / "previews" / "encoded-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"video": result, "elapsed_seconds": round(time.perf_counter()-start, 2)}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--size", type=int, default=SIZE)
    args = parser.parse_args()
    (HERE / "animation_spec.json").write_text(json.dumps(spec(), indent=2) + "\n")
    if args.preview:
        previews()
    if args.render:
        render_video(args.size)


if __name__ == "__main__":
    main()
