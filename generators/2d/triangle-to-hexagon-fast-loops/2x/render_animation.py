#!/usr/bin/env python3
"""Deterministic vector animation: regular polygons morph on a fixed hex grid.

This draws new mathematical geometry. It does not read or modify source images.
The browser preview follows the same specification and perimeter correspondence.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
SIZE = 1080
PITCH = 144.0
ROW_PITCH = PITCH * math.sqrt(3.0) / 2.0
ORIGIN = (72.0, 54.0)
RADIUS = 54.0
STROKE = 2.3
ANTIALIAS = 2
BPM = 124
SPEED_MULTIPLIER = 2
DEFAULT_FPS = 62 * SPEED_MULTIPLIER
SOURCE_BEAT_SECONDS = 60.0 / BPM
STATE_SECONDS = SOURCE_BEAT_SECONDS / SPEED_MULTIPLIER
MORPH_SECONDS = 0.12 / SPEED_MULTIPLIER
HOLD_SECONDS = STATE_SECONDS - MORPH_SECONDS
STATES: list[int | None] = [3, 4, 5, 6]
NAMES = ["Triangle", "Square", "Pentagon", "Hexagon"]
DURATION = len(STATES) * STATE_SECONDS


def perimeter_knots() -> np.ndarray:
    """Exact rational union: every polygon corner plus a smooth circle mesh."""
    knots = {Fraction(i, 240) for i in range(240)}
    for n in range(3, 13):
        if n % 4 == 0:
            knots.update(Fraction(2 * j + 1, 2 * n) for j in range(n))
        else:
            knots.update(Fraction(j, n) for j in range(n))
    return np.asarray([float(u) for u in sorted(knots)], dtype=np.float64)


KNOTS = perimeter_knots()


def outline(n: int | None, u: np.ndarray = KNOTS) -> np.ndarray:
    """Clockwise in screen coordinates, starting at the top of each shape.

    Multiples of four have a flat horizontal top (including the NSEW square).
    All others have a top vertex, matching the previous polygon designs.
    """
    if n is None:
        theta = -math.pi / 2.0 + 2.0 * math.pi * u
        return RADIUS * np.column_stack((np.cos(theta), np.sin(theta)))
    flat_top = n % 4 == 0
    phase = math.pi / n if flat_top else 0.0
    q = n * u - (0.5 if flat_top else 0.0)
    j = np.floor(q).astype(int)
    fraction = q - j
    theta0 = -math.pi / 2.0 + phase + j * (2.0 * math.pi / n)
    theta1 = theta0 + 2.0 * math.pi / n
    a = np.column_stack((np.cos(theta0), np.sin(theta0)))
    b = np.column_stack((np.cos(theta1), np.sin(theta1)))
    return RADIUS * (a * (1.0 - fraction[:, None]) + b * fraction[:, None])


OUTLINES = [outline(n) for n in STATES]


def smootherstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def shape_at(seconds: float) -> tuple[np.ndarray, dict]:
    phase = seconds % DURATION
    index = min(len(STATES) - 1, int(phase / STATE_SECONDS))
    local = phase - index * STATE_SECONDS
    amount = smootherstep((local - HOLD_SECONDS) / MORPH_SECONDS)
    following = (index + 1) % len(STATES)
    points = OUTLINES[index] * (1.0 - amount) + OUTLINES[following] * amount
    return points, {
        "state_index": index,
        "from": NAMES[index],
        "to": NAMES[following],
        "morph_amount": amount,
        "seconds": phase,
    }


def centers() -> np.ndarray:
    locations = []
    reach = RADIUS + STROKE
    for row in range(-2, math.ceil(SIZE / ROW_PITCH) + 3):
        y = ORIGIN[1] + row * ROW_PITCH
        for col in range(-2, math.ceil(SIZE / PITCH) + 3):
            x = ORIGIN[0] + col * PITCH + (row % 2) * PITCH / 2.0
            if -reach <= x <= SIZE + reach and -reach <= y <= SIZE + reach:
                locations.append((x, y))
    return np.asarray(locations, dtype=np.float64)


CENTERS = centers()


def rainbow_field(size: int) -> np.ndarray:
    # h=(x+y)/size advances twice from the upper-left to the lower-right.
    coords = (np.arange(size, dtype=np.float32) + 0.5) / size
    hue6 = ((coords[:, None] + coords[None, :]) % 1.0) * 6.0
    sector = np.floor(hue6).astype(np.int8)
    fraction = hue6 - sector
    rgb = np.zeros((size, size, 3), dtype=np.float32)
    for k in range(6):
        mask = sector == k
        f = fraction[mask]
        one = np.ones_like(f)
        zero = np.zeros_like(f)
        options = [
            (one, f, zero), (1.0 - f, one, zero), (zero, one, f),
            (zero, 1.0 - f, one), (f, zero, one), (one, zero, 1.0 - f),
        ]
        rgb[mask] = np.column_stack(options[k])
    return np.rint(rgb * 255.0).astype(np.uint8)


class Renderer:
    def __init__(self, size: int = SIZE, antialias: int = ANTIALIAS):
        self.size = size
        self.antialias = antialias
        self.scale = size / SIZE
        self.raster_scale = self.scale * antialias
        self.mask = Image.new("L", (size * antialias, size * antialias), 0)
        self.draw = ImageDraw.Draw(self.mask)
        self.width = max(1, round(STROKE * self.raster_scale))
        self.gradient = rainbow_field(size)
        self.gradient16 = self.gradient.astype(np.uint16)
        self.work16 = np.empty_like(self.gradient16)

    def frame(self, seconds: float) -> Image.Image:
        points, _ = shape_at(seconds)
        self.draw.rectangle((0, 0, self.mask.width, self.mask.height), fill=0)
        points = np.vstack((points, points[:1]))
        for center in CENTERS:
            path = (points + center) * self.raster_scale
            self.draw.line([tuple(p) for p in path], fill=255, width=self.width, joint="curve")
        mask = self.mask.resize((self.size, self.size), Image.Resampling.LANCZOS)
        alpha = np.asarray(mask, dtype=np.uint8)
        np.multiply(self.gradient16, alpha[:, :, None], out=self.work16)
        self.work16 += 127
        np.floor_divide(self.work16, 255, out=self.work16)
        return Image.fromarray(self.work16.astype(np.uint8), mode="RGB")


def polygon_area(points: np.ndarray) -> float:
    following = np.roll(points, -1, axis=0)
    return float(np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1]) / 2.0)


def validate() -> dict:
    samples = np.arange(660) * DURATION / 660.0
    maximum_radius = 0.0
    minimum_cross = 1.0
    for seconds in samples:
        points, _ = shape_at(float(seconds))
        maximum_radius = max(maximum_radius, float(np.linalg.norm(points, axis=1).max()))
        edges = np.roll(points, -1, axis=0) - points
        following = np.roll(edges, -1, axis=0)
        crosses = edges[:, 0] * following[:, 1] - edges[:, 1] * following[:, 0]
        minimum_cross = min(minimum_cross, float(crosses.min()))
    areas = []
    for name, n, points in zip(NAMES, STATES, OUTLINES):
        expected = (math.pi * RADIUS ** 2 if n is None else n * RADIUS ** 2 * math.sin(2 * math.pi / n) / 2)
        actual = polygon_area(points)
        areas.append({"shape": name, "relative_area_error": abs(actual - expected) / expected})
    pair_distances = np.linalg.norm(CENTERS[:, None, :] - CENTERS[None, :, :], axis=2)
    np.fill_diagonal(pair_distances, np.inf)
    exact_loop_error = float(np.max(np.abs(shape_at(0.0)[0] - shape_at(DURATION)[0])))
    assert maximum_radius <= RADIUS + 1e-8
    assert minimum_cross >= -1e-7, "An intermediate shape became concave"
    assert all(row["relative_area_error"] < 1e-10 for row in areas)
    assert exact_loop_error == 0.0
    step_checks = []
    for step in range(len(STATES) + 1):
        points, phase = shape_at(step * STATE_SECONDS)
        expected_index = step % len(STATES)
        error = float(np.max(np.abs(points - OUTLINES[expected_index])))
        assert phase["state_index"] == expected_index
        assert error == 0.0
        step_checks.append({"shape_step": step, "frame": round(step * STATE_SECONDS * DEFAULT_FPS), "shape": NAMES[expected_index], "point_error": error})
    return {
        "bpm": BPM,
        "speed_multiplier": SPEED_MULTIPLIER,
        "steps_per_beat": SPEED_MULTIPLIER,
        "effective_shape_changes_per_minute": BPM * SPEED_MULTIPLIER,
        "source_beat_seconds": SOURCE_BEAT_SECONDS,
        "export_fps": DEFAULT_FPS,
        "frames_per_beat": round(SOURCE_BEAT_SECONDS * DEFAULT_FPS),
        "frames_per_shape_step": round(STATE_SECONDS * DEFAULT_FPS),
        "frames_per_loop": round(DURATION * DEFAULT_FPS),
        "duration_seconds": DURATION,
        "state_seconds": STATE_SECONDS,
        "hold_seconds": HOLD_SECONDS,
        "morph_seconds": MORPH_SECONDS,
        "morph_frame_intervals_at_export_fps": round(MORPH_SECONDS * DEFAULT_FPS, 6),
        "shape_step_keyframe_checks": step_checks,
        "perimeter_sample_count": len(KNOTS),
        "grid_center_count_including_edge_clips": len(CENTERS),
        "minimum_center_distance": float(pair_distances.min()),
        "maximum_circumradius_across_660_phases": maximum_radius,
        "minimum_empty_gap_between_bounding_circles": float(pair_distances.min() - 2 * RADIUS),
        "minimum_signed_turn_cross_product": minimum_cross,
        "exact_loop_point_error": exact_loop_error,
        "endpoint_area_checks": areas,
        "canvas": [SIZE, SIZE],
        "color_field": "One fixed spatial HSV field; h=((x+y)/1080)%1, s=v=1",
    }


def make_previews(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    renderer = Renderer(540)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    # Keyframes plus the new direct hexagon/triangle transition.
    times = [i * STATE_SECONDS + HOLD_SECONDS / 2 for i in range(len(STATES))]
    times.append((len(STATES) - 1) * STATE_SECONDS + HOLD_SECONDS + MORPH_SECONDS / 2)
    sheet = Image.new("RGB", (4 * 300, math.ceil(len(times) / 4) * 330), "#101010")
    draw = ImageDraw.Draw(sheet)
    for i, seconds in enumerate(times):
        frame = renderer.frame(seconds)
        frame.resize((300, 300), Image.Resampling.LANCZOS)
        thumb = frame.resize((300, 300), Image.Resampling.LANCZOS)
        x, y = (i % 4) * 300, (i // 4) * 330
        sheet.paste(thumb, (x, y))
        label = NAMES[i] if i < len(NAMES) else "Hexagon → Triangle (50%)"
        draw.text((x + 9, y + 306), label, font=font, fill="#dddddd")
    sheet.save(output / "keyframes-contact-sheet.png")
    large = Renderer(SIZE)
    large.frame(HOLD_SECONDS / 2).save(output / "triangle-frame.png")
    large.frame(STATE_SECONDS + HOLD_SECONDS / 2).save(output / "square-frame.png")
    large.frame(3 * STATE_SECONDS + HOLD_SECONDS / 2).save(output / "hexagon-frame.png")
    large.frame(3 * STATE_SECONDS + HOLD_SECONDS + MORPH_SECONDS / 2).save(output / "hexagon-triangle-midpoint.png")
    validation = validate()
    (output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    benchmark = Renderer(720)
    start = time.perf_counter()
    for i in range(12):
        benchmark.frame(i * DURATION / 12)
    validation["benchmark_720p_frames_per_second"] = 12 / (time.perf_counter() - start)
    print(json.dumps(validation, indent=2))


def render_video(path: Path, size: int, fps: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    renderer = Renderer(size)
    frames = round(DURATION * fps)
    if not math.isclose(DURATION * fps, frames, abs_tol=1e-9) or not math.isclose(STATE_SECONDS * fps, round(STATE_SECONDS * fps), abs_tol=1e-9):
        raise ValueError(f"Use a frame rate divisible by {31 * SPEED_MULTIPLIER} for frame-exact shape steps.")
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{size}x{size}",
        "-framerate", str(fps), "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
        "-video_track_timescale", str(fps * 1000), "-movie_timescale", str(fps * 1000),
        "-movflags", "+faststart", str(path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    start = time.perf_counter()
    hold_frames: dict[int, bytes] = {}
    try:
        assert process.stdin is not None
        for frame_index in range(frames):
            seconds = frame_index / fps
            state_index = int((seconds % DURATION) / STATE_SECONDS)
            local = (seconds % DURATION) - state_index * STATE_SECONDS
            if local <= HOLD_SECONDS:
                if state_index not in hold_frames:
                    hold_frames[state_index] = renderer.frame(state_index * STATE_SECONDS).tobytes()
                frame_bytes = hold_frames[state_index]
            else:
                frame_bytes = renderer.frame(seconds).tobytes()
            process.stdin.write(frame_bytes)
            if frame_index % (fps * 3) == 0:
                print(json.dumps({"frame": frame_index, "total": frames, "seconds_elapsed": round(time.perf_counter() - start, 1)}), flush=True)
        process.stdin.close()
        code = process.wait()
        if code:
            raise RuntimeError(f"ffmpeg exited with {code}")
    except BaseException:
        process.kill()
        process.wait()
        raise
    print(json.dumps({"video": str(path.resolve()), "frames": frames, "fps": fps, "duration": DURATION, "size_bytes": path.stat().st_size, "elapsed_seconds": round(time.perf_counter() - start, 2)}), flush=True)


def write_spec() -> None:
    spec = {
        "title": f"Triangle to hexagon · 124 BPM · {SPEED_MULTIPLIER}×",
        "version": 1,
        "bpm": BPM,
        "speed_multiplier": SPEED_MULTIPLIER,
        "steps_per_beat": SPEED_MULTIPLIER,
        "effective_shape_changes_per_minute": BPM * SPEED_MULTIPLIER,
        "source_beat_seconds": SOURCE_BEAT_SECONDS,
        "beat_seconds": SOURCE_BEAT_SECONDS,
        "beats_per_loop": len(STATES) / SPEED_MULTIPLIER,
        "export_fps": DEFAULT_FPS,
        "frames_per_beat": round(SOURCE_BEAT_SECONDS * DEFAULT_FPS),
        "frames_per_shape_step": round(STATE_SECONDS * DEFAULT_FPS),
        "frames_per_loop": round(DURATION * DEFAULT_FPS),
        "beat_alignment": f"{SPEED_MULTIPLIER} shape steps per 124 BPM beat; each morph occupies the last {MORPH_SECONDS:g} seconds before the next shape step",
        "canvas_size": SIZE,
        "duration_seconds": DURATION,
        "state_seconds": STATE_SECONDS,
        "hold_seconds": HOLD_SECONDS,
        "morph_seconds": MORPH_SECONDS,
        "states": STATES,
        "names": NAMES,
        "radius": RADIUS,
        "stroke_width": STROKE,
        "antialias": ANTIALIAS,
        "grid": {"type": "hexagonal", "pitch": PITCH, "row_pitch": ROW_PITCH, "origin": list(ORIGIN), "odd_row_offset": PITCH / 2},
        "orientation": "Flat top for n%4==0; vertex up otherwise; all paths start at their topmost point and proceed clockwise",
        "easing": f"smootherstep: x^3*(x*(6*x-15)+10), x=clamp((localTime-{HOLD_SECONDS:.15g})/{MORPH_SECONDS:.15g},0,1)",
        "perimeter_knots": KNOTS.tolist(),
        "color": {"hue": "((x+y)/1080)%1", "saturation": 1, "value": 1, "background": "#000000", "temporal_drift": False},
        "centers": CENTERS.tolist(),
    }
    (HERE / "animation_spec.json").write_text(json.dumps(spec, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    args = parser.parse_args()
    write_spec()
    if args.preview:
        make_previews(HERE / "previews")
    if args.video:
        render_video(args.video, args.size, args.fps)
    if not args.preview and not args.video:
        print(json.dumps(validate(), indent=2))


if __name__ == "__main__":
    main()
