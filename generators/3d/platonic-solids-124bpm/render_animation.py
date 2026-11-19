#!/usr/bin/env python3
"""Render exact 3D wireframe solids morphing on a fixed hexagonal grid.

Each line is carried by a continuously changing convex radial surface. Outgoing
and incoming edge networks are weighted during the brief topology transition.
The scene is projected orthographically from +Z, with screen Y=-world Y.
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
PITCH = 144.0
ROW_PITCH = PITCH * math.sqrt(3) / 2
ORIGIN = (72.0, 54.0)
ANTIALIAS = 3
REAR_INTENSITY = 0.14
BPM = 124
BASE_STEP = Fraction(60, BPM)
BASE_MORPH = 0.12
FRAMES_PER_STEP = 30
GEOMETRY = json.loads((HERE / "geometry.json").read_text())
SHAPES = GEOMETRY["shapes"]
NAMES = [s["label"] for s in SHAPES]
FRAME_COUNT = len(SHAPES) * FRAMES_PER_STEP


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


def state_at(seconds: float, speed: int = 2) -> dict:
    step = float(BASE_STEP / speed)
    duration = step * len(SHAPES)
    local = seconds % duration
    position = local / step
    nearest = round(position)
    if abs(position - nearest) <= 1e-10:
        index = nearest % len(SHAPES)
        elapsed = 0.0
    else:
        index = min(len(SHAPES) - 1, int(position))
        elapsed = local - index * step
    morph = BASE_MORPH / speed
    blend = smootherstep((elapsed - (step - morph)) / morph)
    return {"index": index, "next": (index + 1) % len(SHAPES),
            "blend": blend, "from": NAMES[index],
            "to": NAMES[(index + 1) % len(SHAPES)], "seconds": local}


def gauge_and_gradient(shape_index: int, directions: np.ndarray):
    """Gauge max(n·u/d), plus the most front-facing active gradient at ties."""
    shape = SHAPES[shape_index]
    if shape["kind"] == "sphere":
        return np.ones(len(directions)), directions.copy()
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
        tile = self.motif(index, blend)
        mask = Image.new("L", (self.size * self.antialias,) * 2, 0)
        for center in CENTERS:
            x, y = center * self.raster_scale
            mask.paste(tile, (round(x) - self.half_tile, round(y) - self.half_tile))
        mask = mask.resize((self.size, self.size), Image.Resampling.LANCZOS)
        alpha = np.asarray(mask, dtype=np.uint16)
        result = (self.gradient16 * alpha[:, :, None] + 127) // 255
        return Image.fromarray(result.astype(np.uint8))

    def frame(self, seconds: float, speed: int = 2) -> Image.Image:
        state = state_at(seconds, speed)
        return self.frame_state(state["index"], state["blend"])


def spec() -> dict:
    variants = []
    for speed in (2, 4):
        step = BASE_STEP / speed
        duration = step * len(SHAPES)
        variants.append({"speed_multiplier": speed, "shape_changes_per_beat": speed,
                         "frame_rate": 62 * speed, "frames_per_shape": 30,
                         "frames_per_loop": FRAME_COUNT,
                         "state_seconds": float(step),
                         "hold_seconds": float(step) - BASE_MORPH / speed,
                         "morph_seconds": BASE_MORPH / speed,
                         "duration_seconds": float(duration),
                         "duration_fraction": str(duration),
                         "beats_per_loop": len(SHAPES) / speed,
                         "video": f"platonic-solids-124bpm-{speed}x.mp4"})
    return {"title": "Platonic solids to sphere · 124 BPM", "version": 1,
            "bpm": BPM, "size": [SIZE, SIZE], "variants": variants,
            "sequence": [s["id"] for s in SHAPES],
            "names": NAMES, "loop_target": "tetrahedron",
            "projection": GEOMETRY["projection"],
            "geometry_file": "geometry.json", "radius": RADIUS,
            "stroke_width": STROKE, "antialias": ANTIALIAS,
            "rear_line_intensity": REAR_INTENSITY,
            "grid": {"type": "hexagonal", "pitch": PITCH,
                     "row_pitch": ROW_PITCH, "origin": ORIGIN,
                     "odd_row_offset": PITCH / 2, "centers": CENTERS.tolist()},
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
    assert len(CENTERS) == 72
    renderer = Renderer(360)
    endpoint_checks = []
    for index in range(len(SHAPES)):
        a = np.asarray(renderer.frame_state(index, 1))
        b = np.asarray(renderer.frame_state((index + 1) % len(SHAPES), 0))
        error = int(np.abs(a.astype(int) - b.astype(int)).max())
        assert error == 0
        endpoint_checks.append({"from": NAMES[index], "to": NAMES[(index + 1) % len(SHAPES)], "pixel_error": error})
    keyframes = []
    for speed in (2, 4):
        duration = float(BASE_STEP / speed * len(SHAPES))
        assert renderer.frame(0, speed).tobytes() == renderer.frame(duration, speed).tobytes()
        for index in range(len(SHAPES)):
            state = state_at(float(BASE_STEP / speed * index), speed)
            assert state["index"] == index and state["blend"] == 0
            keyframes.append({"speed": speed, "frame": index * 30, "shape": NAMES[index]})
    return {"topology": "passed", "fixed_centers": len(CENTERS),
            "endpoint_checks": endpoint_checks, "exact_loop_closure": True,
            "keyframes": keyframes}


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


def render_videos(speeds: list[int], size: int = SIZE) -> list[dict]:
    renderer = Renderer(size)
    processes = []
    start = time.perf_counter()
    for speed in speeds:
        fps = 62 * speed
        path = HERE / f"platonic-solids-124bpm-{speed}x.mp4"
        command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                   "-f", "rawvideo", "-pixel_format", "rgb24",
                   "-video_size", f"{size}x{size}", "-framerate", str(fps),
                   "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "medium",
                   "-crf", "16", "-pix_fmt", "yuv420p",
                   "-video_track_timescale", str(fps * 1000),
                   "-movie_timescale", str(fps * 1000), "-movflags", "+faststart", str(path)]
        processes.append((speed, path, subprocess.Popen(command, stdin=subprocess.PIPE)))
    cache = {}
    try:
        for frame_index in range(FRAME_COUNT):
            state = state_at(frame_index / 124, 2)
            if state["blend"] <= 0:
                if state["index"] not in cache:
                    cache[state["index"]] = renderer.frame_state(state["index"], 0).tobytes()
                data = cache[state["index"]]
            else:
                data = renderer.frame_state(state["index"], state["blend"]).tobytes()
            for _, _, process in processes:
                assert process.stdin is not None
                process.stdin.write(data)
            if frame_index % 30 == 0:
                print(json.dumps({"frame": frame_index, "total": FRAME_COUNT}), flush=True)
        for _, _, process in processes:
            process.stdin.close()
        for _, _, process in processes:
            if process.wait():
                raise RuntimeError("FFmpeg failed")
    except BaseException:
        for _, _, process in processes:
            process.kill()
            process.wait()
        raise
    results = []
    for speed, path, _ in processes:
        probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,time_base,duration_ts,start_time", "-of", "json", str(path)]))["streams"][0]
        assert int(probe["nb_frames"]) == FRAME_COUNT
        assert Fraction(probe["avg_frame_rate"]) == 62 * speed
        actual_duration = int(probe["duration_ts"]) * Fraction(probe["time_base"])
        expected_duration = BASE_STEP / speed * len(SHAPES)
        assert actual_duration == expected_duration
        assert float(probe["start_time"]) == 0
        results.append({"path": str(path), "speed": speed, "frames": FRAME_COUNT,
                        "fps": 62 * speed, "duration": str(actual_duration),
                        "bytes": path.stat().st_size, "stream": probe})
    (HERE / "previews").mkdir(exist_ok=True)
    (HERE / "previews" / "encoded-validation.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"videos": results, "elapsed_seconds": round(time.perf_counter()-start, 2)}), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--speed", choices=["2", "4", "both"], default="both")
    parser.add_argument("--size", type=int, default=SIZE)
    args = parser.parse_args()
    (HERE / "animation_spec.json").write_text(json.dumps(spec(), indent=2) + "\n")
    if args.preview:
        previews()
    if args.render:
        render_videos([2, 4] if args.speed == "both" else [int(args.speed)], args.size)


if __name__ == "__main__":
    main()
