"""Exact tesseract graph and projective morph, shared by Python and browser.

Screen coordinates are P @ vertex / (1 - q @ vertex), with no extra Y flip.
After projection, subtract the midpoint of the vertex bounding box and scale
uniformly to a maximum vertex radius of 52. Parameter and intensity blends use
one quintic-eased interpolation parameter. All 32 graph edges remain present.

Signed coordinate permutations change vertex correspondence while preserving
the three previously approved endpoint images. These are projective morphs,
not a claim that interpolation of P is a rigid rotation in four dimensions.
"""

from itertools import combinations, product
from pathlib import Path
import json
import math

import numpy as np

OUT = Path(__file__).resolve().parent
VERTICES = np.array(list(product([-1.0, 1.0], repeat=4)))
EDGES = [(i, j) for i, j in combinations(range(16), 2)
         if np.count_nonzero(VERTICES[i] != VERTICES[j]) == 1]
RADIUS = 52.0
PITCH = 108.0
LINE_WIDTH = 2.0


def normalize(direction):
    direction = np.asarray(direction, dtype=float)
    return direction / np.linalg.norm(direction)


def cube_intensities(camera):
    camera = normalize(camera)
    result = []
    for i, j in EDGES:
        axis = int(np.flatnonzero(VERTICES[i] != VERTICES[j])[0])
        if axis == 3:
            bright = float(VERTICES[i, :3] @ camera) >= 0
        else:
            bright = any(VERTICES[i, a] * camera[a] > 0
                         for a in range(3) if a != axis)
        result.append(1.0 if bright else 108.0 / 210.0)
    return np.array(result)


def canonical_poses():
    cam = normalize([1.6, 1.1, 2.4])
    right = normalize(np.cross([0.0, 1.0, 0.0], cam))
    up = np.cross(cam, right)
    angles = np.arange(4) * math.pi / 4 + math.pi / 8
    oct_intensities = [
        1.0 if int(np.flatnonzero(VERTICES[i] != VERTICES[j])[0]) in (0, 2)
        else 135.0 / 210.0 for i, j in EDGES
    ]
    return [
        dict(id="classic", label="Classic nested cubes",
             P=np.column_stack((np.vstack((right, -up)), np.zeros(2))),
             q=np.array([0, 0, 0, 1 / 3.8]),
             edge_intensities=cube_intensities(cam)),
        dict(id="frontal", label="Frontal square depth",
             P=np.array([[1, 0, .28, 0], [0, -1, -.20, 0]]),
             q=np.array([0, 0, 0, 1 / 3.6]),
             edge_intensities=cube_intensities([.28, .20, 1])),
        dict(id="octagonal", label="Octagonal projection",
             P=np.vstack((np.cos(angles), np.sin(angles))),
             q=np.zeros(4), edge_intensities=np.array(oct_intensities)),
    ]


def remap_pose(pose, automorphism):
    """Relabel Q4 vertices and edge brightness without altering its picture."""
    lookup = {tuple(v): i for i, v in enumerate(VERTICES)}
    vertex_map = [lookup[tuple(v)] for v in VERTICES @ automorphism.T]
    edge_lookup = {edge: k for k, edge in enumerate(EDGES)}
    edge_map = [edge_lookup[tuple(sorted((vertex_map[i], vertex_map[j])))]
                for i, j in EDGES]
    return dict(
        id=pose["id"], label=pose["label"],
        P=(pose["P"] @ automorphism).tolist(),
        q=(pose["q"] @ automorphism).tolist(),
        edge_intensities=pose["edge_intensities"][edge_map].tolist(),
        coordinate_automorphism=automorphism.astype(int).tolist(),
    )


def project_pose(pose, radius=RADIUS, vertices=VERTICES):
    P = np.asarray(pose["P"], dtype=float)
    q = np.asarray(pose["q"], dtype=float)
    xy = (vertices @ P.T) / (1 - vertices @ q)[:, None]
    xy -= (xy.min(axis=0) + xy.max(axis=0)) / 2
    xy *= radius / np.linalg.norm(xy, axis=1).max()
    return xy


def quintic(u):
    return u * u * u * (u * (6 * u - 15) + 10)


def interpolate_pose(start, end, amount):
    """amount is already eased; use quintic(u) for animation playback."""
    return {key: (np.asarray(start[key]) * (1 - amount)
                  + np.asarray(end[key]) * amount)
            for key in ("P", "q", "edge_intensities")}


def pose_at_frame(geometry, frame):
    frame = frame % 720
    index = int(frame // 240)
    local = frame % 240
    u = 0.0 if local < 180 else (local - 180) / 60
    return interpolate_pose(geometry["poses"][index],
                            geometry["poses"][(index + 1) % 3], quintic(u))


def validate(poses):
    minimum_distance = math.inf
    minimum_denominator = math.inf
    minimum_singular = math.inf
    where = None
    sample_count = 2001
    for index, start in enumerate(poses):
        end = poses[(index + 1) % 3]
        for u in np.linspace(0, 1, sample_count):
            pose = interpolate_pose(start, end, u)
            xy = project_pose(pose)
            distances = np.linalg.norm(xy[:, None] - xy[None, :], axis=2)
            np.fill_diagonal(distances, np.inf)
            distance = float(distances.min())
            if distance < minimum_distance:
                minimum_distance, where = distance, [index, float(u)]
            minimum_denominator = min(minimum_denominator,
                                      float((1 - VERTICES @ pose["q"]).min()))
            minimum_singular = min(minimum_singular,
                                   float(np.linalg.svd(pose["P"], compute_uv=False)[-1]))
    assert len(VERTICES) == 16 and len(EDGES) == 32
    assert all(sum(i in edge for edge in EDGES) == 4 for i in range(16))
    assert minimum_distance > 2.5 and minimum_denominator > .72
    return dict(
        vertices=16, edges=32, degree_each_vertex=4,
        parameter_samples=3 * sample_count,
        minimum_projected_vertex_distance_px=minimum_distance,
        closest_vertices_at_transition_and_parameter=where,
        minimum_projection_denominator=minimum_denominator,
        minimum_P_singular_value=minimum_singular,
        bounding_circle_gap_px=PITCH - 2 * RADIUS,
        minimum_stroke_clearance_px=PITCH - 2 * RADIUS - LINE_WIDTH,
        clearance_proof="Every line segment is in its radius-52 disk. "
                        "Nearest lattice centers are 108 apart, leaving at "
                        "least 4 pixels between graphs or 2 pixels between "
                        "strokes of width 2, at every interpolation parameter.",
    )


def build_geometry():
    originals = canonical_poses()
    automorphisms = [np.eye(4),
        np.array([[0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]),
        np.array([[0, 0, 0, 1], [0, 0, -1, 0], [0, 1, 0, 0], [1, 0, 0, 0]])]
    poses = [remap_pose(pose, A) for pose, A in zip(originals, automorphisms)]
    # Every endpoint is the source image with only its vertex numbering changed.
    vertex_lookup = {tuple(v): i for i, v in enumerate(VERTICES)}
    for original, pose, A in zip(originals, poses, automorphisms):
        mapping = [vertex_lookup[tuple(v)] for v in VERTICES @ A.T]
        assert np.allclose(project_pose(pose), project_pose(original)[mapping], atol=1e-12)
    return dict(
        schema_version=1,
        vertices=VERTICES.astype(int).tolist(), edges=[list(e) for e in EDGES],
        poses=poses, radius=RADIUS, pitch=PITCH,
        row_pitch=PITCH * math.sqrt(3) / 2,
        line_width=LINE_WIDTH,
        timing=dict(fps=124, bpm=124, frames_per_beat=60,
                    hold_frames=180, morph_frames=60, frames_per_pose=240,
                    frames_per_cycle=720, cycles=2, frame_count=1440,
                    duration_seconds=1440 / 124),
        algorithm=dict(
            projection="xy = (P @ v) / (1 - q @ v); P rows are screen X,Y",
            centering="Subtract (min_xy + max_xy) / 2 across all 16 vertices",
            scaling="Multiply all xy by radius / max(norm(xy))",
            interpolation="Linearly blend P, q and edge_intensities using s=6u^5-15u^4+10u^3",
            intensities="Normalized 0..1. Retain all 32 edges; composite dimmest first.",
            frame_schedule="i=floor((f%720)/240); local=f%240; u=local<180?0:(local-180)/60; blend pose i to (i+1)%3",
            endpoint_relabeling="Signed 4D coordinate permutations preserve every endpoint graph and intensity; no intermediate waypoints needed.",
        ),
        validation=validate(poses),
    )


def contact_sheet(geometry, destination):
    """Temporary mathematical diagram for QA, never modifies source imagery."""
    from PIL import Image, ImageDraw, ImageFont
    scale = 3
    sheet = Image.new("RGB", (1200 * scale, 800 * scale), "black")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17 * scale)
    except OSError:
        font = ImageFont.load_default()
    for row in range(2):
        for column in range(3):
            start = geometry["poses"][column]
            end = geometry["poses"][(column + 1) % 3]
            pose = start if row == 0 else interpolate_pose(start, end, .5)
            xy = project_pose(pose, 143)
            xy += [200 + column * 400, 186 + row * 400]
            order = np.argsort(pose["edge_intensities"])
            for k in order:
                i, j = EDGES[k]
                gray = int(round(220 * pose["edge_intensities"][k]))
                draw.line([tuple(xy[i] * scale), tuple(xy[j] * scale)],
                          fill=(gray,) * 3, width=4 * scale)
            label = start["label"] if row == 0 else start["id"] + " to " + end["id"] + " halfway"
            draw.text(((column * 400 + 20) * scale, (row * 400 + 365) * scale),
                      label, fill=(220, 220, 220), font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.resize((1200, 800), Image.Resampling.LANCZOS).save(destination)


if __name__ == "__main__":
    data = build_geometry()
    path = OUT / "geometry.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    preview = OUT.parent / "tmp" / "hypercube_morph" / "geometry_contact_sheet.png"
    contact_sheet(data, preview)
    print(json.dumps(dict(geometry=str(path), contact_sheet=str(preview),
                         validation=data["validation"]), indent=2))
