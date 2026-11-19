#!/usr/bin/env python3
"""Render five Platonic solids on a tight hexagonal grid at 124 BPM.

Each line is carried by a continuously changing convex radial surface. Outgoing
and incoming edge networks are weighted during each one-beat transition.
The scene is projected orthographically from +Z, with screen Y=-world Y.
The five-solid cycle repeats twice, producing a 19.35-second video.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SIZE = 1080
RADIUS = 54.0
STROKE = 2.0
PITCH = 108.0
ROW_PITCH = PITCH * math.sqrt(3) / 2
ORIGIN = (54.0, 54.0)
ANTIALIAS = 3
REAR_INTENSITY = 0.14
BPM = 124
FPS = 124
BEAT_SECONDS = Fraction(60, BPM)
STATE_SECONDS = BEAT_SECONDS * 4
HOLD_SECONDS = BEAT_SECONDS * 3
MORPH_SECONDS = BEAT_SECONDS
FRAMES_PER_STEP = int(STATE_SECONDS * FPS)
GEOMETRY = json.loads((HERE / "geometry.json").read_text())
SHAPES = GEOMETRY["shapes"]
NAMES = [s["label"] for s in SHAPES]
LOOP_REPEATS = 2
STEP_COUNT = len(SHAPES) * LOOP_REPEATS
FRAME_COUNT = STEP_COUNT * FRAMES_PER_STEP
CYCLE_DURATION = STATE_SECONDS * len(SHAPES)
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
    duration = float(DURATION)
    local = seconds % duration
    position = local / step
    nearest = round(position)
    if abs(position - nearest) <= 1e-10:
        step_index = nearest % STEP_COUNT
        elapsed = 0.0
    else:
        step_index = min(STEP_COUNT - 1, int(position))
        elapsed = local - step_index * step
    index = step_index % len(SHAPES)
    blend = smootherstep((elapsed - float(HOLD_SECONDS)) / float(MORPH_SECONDS))
    return {"index": index, "step_index": step_index,
            "cycle": step_index // len(SHAPES), "next": (index + 1) % len(SHAPES),
            "blend": blend, "from": NAMES[index],
            "to": NAMES[(index + 1) % len(SHAPES)], "seconds": local}


def gauge_and_gradient(shape_index: int, directions: np.ndarray):
    """Gauge max(n·u/d), plus the most front-facing active gradient at ties."""
    shape = SHAPES[shape_index]
    planes = np.asarray(shape["planes"], dtype=float)
    gradients = planes[:, :3] / planes[:, 3:4]
    scores = directions @ gradients.T
    gauge = np.max(scores, axis=1)
    tied = np.abs(scores - gauge[:, None]) <= 2e-6
    selected = np.argmax(np.where(tied, gradients[None, :, 2], -np.inf), axis=1)
    return gauge, gradients[selected]


@dataclass
class PreparedGraph:
    directions: np.ndarray  # [segment, endpoint, xyz]
    gauge_a: np.ndarray
    gauge_b: np.ndarray
    gradient_a: np.ndarray  # [segment, xyz], sampled at spherical midpoint
    gradient_b: np.ndarray


def prepared_paths(path_shape: int, source_shape: int, target_shape: int) -> PreparedGraph:
    segments = []
    for path in SHAPES[path_shape]["paths"]:
        u = np.asarray(path["directions"], dtype=float)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        if path.get("closed", False) and np.linalg.norm(u[-1] - u[0]) > 1e-8:
            u = np.vstack((u, u[0]))
        segments.append(np.stack((u[:-1], u[1:]), axis=1))
    directions = np.concatenate(segments)
    flat = directions.reshape((-1, 3))
    gauge_a, _ = gauge_and_gradient(source_shape, flat)
    gauge_b, _ = gauge_and_gradient(target_shape, flat)
    midpoint = np.sum(directions, axis=1)
    midpoint /= np.linalg.norm(midpoint, axis=1, keepdims=True)
    _, gradient_a = gauge_and_gradient(source_shape, midpoint)
    _, gradient_b = gauge_and_gradient(target_shape, midpoint)
    return PreparedGraph(directions, gauge_a.reshape((-1, 2)),
                         gauge_b.reshape((-1, 2)), gradient_a, gradient_b)


TRANSITIONS = [(prepared_paths(i, i, (i + 1) % len(SHAPES)),
                prepared_paths((i + 1) % len(SHAPES), i, (i + 1) % len(SHAPES)))
               for i in range(len(SHAPES))]


def graph_at(graph: PreparedGraph, blend: float):
    gauge = graph.gauge_a * (1 - blend) + graph.gauge_b * blend
    points = graph.directions / gauge[:, :, None]
    gradient = graph.gradient_a * (1 - blend) + graph.gradient_b * blend
    facing = gradient[:, 2] / np.linalg.norm(gradient, axis=1)
    visibility = np.clip((facing + 0.06) / 0.06, 0, 1)
    visibility = visibility * visibility * (3 - 2 * visibility)
    intensity = REAR_INTENSITY + (1 - REAR_INTENSITY) * visibility
    return points[:, :, :2] * np.array([RADIUS, -RADIUS]), intensity


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

    def graph_mask(self, graph: PreparedGraph, blend: float) -> Image.Image:
        points, brightness = graph_at(graph, blend)
        pixels = points * self.raster_scale + self.half_tile
        mask = Image.new("L", (self.tile_size, self.tile_size), 0)
        draw = ImageDraw.Draw(mask)
        for i in np.argsort(brightness, kind="stable"):
            draw.line([tuple(pixels[i, 0]), tuple(pixels[i, 1])],
                      fill=round(float(brightness[i]) * 255), width=self.width)
        return mask

    def motif(self, index: int, blend: float) -> Image.Image:
        outgoing, incoming = TRANSITIONS[index]
        if blend <= 0:
            return self.graph_mask(outgoing, 0)
        if blend >= 1:
            return self.graph_mask(incoming, 1)
        a = np.asarray(self.graph_mask(outgoing, blend), dtype=float)
        b = np.asarray(self.graph_mask(incoming, blend), dtype=float)
        return Image.fromarray(np.rint(a * (1 - blend) + b * blend).astype(np.uint8))

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
        mask = Image.fromarray(mask_pixels)
        mask = mask.resize((self.size, self.size), Image.Resampling.LANCZOS)
        alpha = np.asarray(mask, dtype=np.uint16)
        result = (self.gradient16 * alpha[:, :, None] + 127) // 255
        return Image.fromarray(result.astype(np.uint8))

    def frame(self, seconds: float) -> Image.Image:
        state = state_at(seconds)
        return self.frame_state(state["index"], state["blend"])


def spec() -> dict:
    return {"title": "Five Platonic solids · Slow tight grid · 124 BPM", "version": 2,
            "bpm": BPM, "size": [SIZE, SIZE], "variant": "slow-tight",
            "frame_rate": FPS, "frames_per_loop": FRAME_COUNT,
            "frames_per_shape": FRAMES_PER_STEP,
            "hold_frames": int(HOLD_SECONDS * FPS),
            "morph_frames": int(MORPH_SECONDS * FPS),
            "beat_seconds": float(BEAT_SECONDS), "beats_per_shape": 4,
            "hold_beats": 3, "morph_beats": 1,
            "beats_per_loop": 4 * STEP_COUNT, "bars_per_loop": STEP_COUNT,
            "cycles_per_video": LOOP_REPEATS, "shapes_per_cycle": len(SHAPES),
            "steps_per_video": STEP_COUNT,
            "cycle_duration_seconds": float(CYCLE_DURATION),
            "cycle_duration_fraction": str(CYCLE_DURATION),
            "state_seconds": float(STATE_SECONDS),
            "hold_seconds": float(HOLD_SECONDS),
            "morph_seconds": float(MORPH_SECONDS),
            "duration_seconds": float(DURATION), "duration_fraction": str(DURATION),
            "video": "platonic-solids-124bpm-slow.mp4",
            "sequence": [s["id"] for s in SHAPES],
            "names": NAMES, "loop_target": "tetrahedron",
            "projection": GEOMETRY["projection"],
            "geometry_file": "geometry.json", "radius": RADIUS,
            "stroke_width": STROKE, "antialias": ANTIALIAS,
            "rear_line_intensity": REAR_INTENSITY,
            "grid": {"type": "hexagonal", "pitch": PITCH,
                     "row_pitch": ROW_PITCH, "origin": ORIGIN,
                     "odd_row_offset": PITCH / 2, "centers": CENTERS.tolist(),
                     "compositing": "clipped per-pixel maximum, preserving adjacent motifs"},
            "morph": {"surface": "Convex radial gauge interpolation",
                      "geometry": "u / ((1-t)*gaugeA(u)+t*gaugeB(u))",
                      "topology": "Deform outgoing and incoming edge networks on the same surface, opacity weights 1-t and t",
                      "easing": "quintic smootherstep",
                      "visibility": ".14+.86*smoothstep(-.06,0,normal.z/length(normal))"},
            "color": {"hue": "((x+y)/1080)%1", "saturation": 1,
                      "value": 1, "background": "#000000", "temporal_drift": False}}


def validate() -> dict:
    expected = [(4, 6, 4), (8, 12, 6), (6, 12, 8), (20, 30, 12), (12, 30, 20)]
    for shape, counts in zip(SHAPES, expected):
        assert (len(shape["vertices"]), len(shape["edges"]), len(shape["faces"])) == counts
        assert counts[0] - counts[1] + counts[2] == 2
    assert [s["id"] for s in SHAPES] == ["tetrahedron", "cube", "octahedron", "dodecahedron", "icosahedron"]
    assert len(CENTERS) == 149
    renderer = Renderer(360)
    endpoint_checks = []
    for index in range(len(SHAPES)):
        a = np.asarray(renderer.frame_state(index, 1))
        b = np.asarray(renderer.frame_state((index + 1) % len(SHAPES), 0))
        error = int(np.abs(a.astype(int) - b.astype(int)).max())
        assert error == 0
        endpoint_checks.append({"from": NAMES[index], "to": NAMES[(index + 1) % len(SHAPES)], "pixel_error": error})
    keyframes = []
    assert float(DURATION) >= 10
    assert FRAME_COUNT == 2400 and FRAMES_PER_STEP == 240 and LOOP_REPEATS == 2
    assert renderer.frame(0).tobytes() == renderer.frame(float(DURATION)).tobytes()
    assert renderer.frame(0).tobytes() == renderer.frame(float(CYCLE_DURATION)).tobytes()
    for step_index in range(STEP_COUNT):
        index = step_index % len(SHAPES)
        start = STATE_SECONDS * step_index
        state = state_at(float(start))
        hold_end = state_at(float(start + HOLD_SECONDS))
        midpoint = state_at(float(start + HOLD_SECONDS + MORPH_SECONDS / 2))
        assert state["index"] == index and state["blend"] == 0 and state["step_index"] == step_index
        assert hold_end["index"] == index and hold_end["blend"] < 1e-12
        assert midpoint["index"] == index and abs(midpoint["blend"] - 0.5) < 1e-12
        keyframes.append({"frame": step_index * FRAMES_PER_STEP, "shape": NAMES[index],
                          "cycle": step_index // len(SHAPES),
                          "seconds": float(start), "hold_beats": 3, "morph_beats": 1})
    return {"topology": "passed", "fixed_centers": len(CENTERS),
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
        frame.save(out / f"{SHAPES[index]['id']}-pattern.png")
        x, y = (index % 3) * 360, (index // 3) * 386
        sheet.paste(frame, (x, y + 26))
        draw.text((x + 12, y + 6), name, fill=(220, 220, 220))
    sheet.save(out / "keyframes-contact-sheet.png")
    morph_sheet = Image.new("RGB", (1080, 772), (8, 8, 8))
    draw = ImageDraw.Draw(morph_sheet)
    for index in range(len(SHAPES)):
        frame = renderer.frame_state(index, 0.5)
        x, y = (index % 3) * 360, (index // 3) * 386
        morph_sheet.paste(frame, (x, y + 26))
        draw.text((x + 10, y + 6), f"{NAMES[index]} to {NAMES[(index+1)%len(SHAPES)]}", fill=(220, 220, 220))
    morph_sheet.save(out / "morph-midpoints-contact-sheet.png")
    (out / "validation.json").write_text(json.dumps(validate(), indent=2) + "\n")


def render_video(size: int = SIZE) -> dict:
    renderer = Renderer(size)
    start = time.perf_counter()
    path = HERE / "platonic-solids-124bpm-slow.mp4"
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
    result = {"path": str(path), "variant": "slow-tight", "frames": FRAME_COUNT,
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
