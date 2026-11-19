"""Build the five exact Platonic solids for radial morphs.

Coordinates are view-space, right handed, with the camera on +Z. Draw x,-y.
Each shape has circumradius 1. Planes satisfy dot(normal, point) <= d.
The positive homogeneous gauge is max(dot(normal,direction)/d); for a
sphere it is length(direction). Interpolating two convex gauges gives a
convex intermediate radial surface. Edge directions are sampled from the
original straight edges, so evaluating the source gauge recovers each edge.

Requires NumPy and SciPy. Pillow is needed only for --preview-dir.
"""

from __future__ import annotations

import argparse
from itertools import combinations, product
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull


PHI = (1.0 + math.sqrt(5.0)) / 2.0
SIGNS = (-1, 1)
EDGE_INTERVALS = 12
CIRCLE_INTERVALS = 72


def unit(v):
    a = np.asarray(v, dtype=float)
    return a / np.linalg.norm(a, axis=-1, keepdims=True)


def canonical_vertices():
    return {
        "tetrahedron": np.array([
            [-1, -1 / math.sqrt(6), -1 / math.sqrt(3)],
            [1, -1 / math.sqrt(6), -1 / math.sqrt(3)],
            [0, -1 / math.sqrt(6), 2 / math.sqrt(3)],
            [0, 3 / math.sqrt(6), 0],
        ]),
        "cube": np.array(list(product(SIGNS, repeat=3)), dtype=float),
        "octahedron": np.vstack((np.eye(3), -np.eye(3))),
        "dodecahedron": np.array(
            list(product(SIGNS, repeat=3))
            + [(0, a / PHI, b * PHI) for a, b in product(SIGNS, repeat=2)]
            + [(a / PHI, b * PHI, 0) for a, b in product(SIGNS, repeat=2)]
            + [(a * PHI, 0, b / PHI) for a, b in product(SIGNS, repeat=2)],
            dtype=float,
        ),
        "icosahedron": np.array(
            [(0, a, b * PHI) for a, b in product(SIGNS, repeat=2)]
            + [(a, b * PHI, 0) for a, b in product(SIGNS, repeat=2)]
            + [(a * PHI, 0, b) for a, b in product(SIGNS, repeat=2)],
            dtype=float,
        ),
    }


CAMERAS = {
    "tetrahedron": ([0.3, 5.0, 0.7], 0.0),
    "cube": ([1.2, 1.0, 1.5], 0.0),
    "octahedron": ([1.0, 1.0, 1.0], 0.0),
    "dodecahedron": ([0.0, PHI, 1.0], 0.0),
    "icosahedron": ([1.0, 1.0, 1.0], 22.238756092964948),
}

EXPECTED = {
    "tetrahedron": (4, 6, 4, 3, 3),
    "cube": (8, 12, 6, 3, 4),
    "octahedron": (6, 12, 8, 4, 3),
    "dodecahedron": (20, 30, 12, 3, 5),
    "icosahedron": (12, 30, 20, 5, 3),
}


def camera_matrix(direction, screen_roll=0.0):
    forward = unit(direction)
    right = unit(np.cross([0.0, 1.0, 0.0], forward))
    up = np.cross(forward, right)
    basis = np.stack((right, up, forward))
    # Positive screen roll is clockwise because screen y = -view y.
    angle = math.radians(-screen_roll)
    roll = np.array([
        [math.cos(angle), -math.sin(angle), 0.0],
        [math.sin(angle), math.cos(angle), 0.0],
        [0.0, 0.0, 1.0],
    ])
    return roll @ basis


def ordered_face(vertices, ids, normal):
    ids = list(ids)
    center = vertices[ids].mean(axis=0)
    axis = unit(vertices[ids[0]] - center)
    tangent = np.cross(normal, axis)
    angles = [math.atan2(float((vertices[i] - center) @ tangent),
                         float((vertices[i] - center) @ axis)) for i in ids]
    return [int(ids[i]) for i in np.argsort(angles)]


def solid_geometry(name, raw_vertices):
    vertices = raw_vertices / np.linalg.norm(raw_vertices[0])
    camera, roll = CAMERAS[name]
    vertices = vertices @ camera_matrix(camera, roll).T
    distances = [(a, b, np.linalg.norm(vertices[a] - vertices[b]))
                 for a, b in combinations(range(len(vertices)), 2)]
    shortest = min(d for _, _, d in distances)
    edges = [(a, b) for a, b, d in distances if abs(d - shortest) < 1e-8]

    # ConvexHull triangulates planar faces. Merge coplanar triangles to recover
    # the exact squares and pentagons instead of drawing artificial diagonals.
    hull = ConvexHull(vertices)
    groups = {}
    for triangle, equation in zip(hull.simplices, hull.equations):
        key = tuple(np.round(equation, 8))
        if key not in groups:
            groups[key] = {"ids": set(), "normal": equation[:3], "d": -equation[3]}
        groups[key]["ids"].update(map(int, triangle))
    groups = sorted(groups.values(), key=lambda face: tuple(np.round(face["normal"], 7)))
    planes = [np.r_[face["normal"], face["d"]].tolist() for face in groups]
    faces = [ordered_face(vertices, face["ids"], face["normal"]) for face in groups]
    paths = []
    for a, b in edges:
        adjacent = [i for i, face in enumerate(faces) if a in face and b in face]
        assert len(adjacent) == 2
        t = np.linspace(0.0, 1.0, EDGE_INTERVALS + 1)[:, None]
        samples = vertices[a] * (1.0 - t) + vertices[b] * t
        directions = unit(samples)
        paths.append({
            "directions": directions.tolist(),
            "closed": False,
            "role": "edge",
            "edge": [a, b],
            "adjacent_faces": adjacent,
        })

    result = {
        "id": name,
        "name": name,
        "label": name.capitalize(),
        "kind": "polyhedron",
        "radius": 1.0,
        "vertices": vertices.tolist(),
        "faces": faces,
        "planes": planes,
        "edges": [list(edge) for edge in edges],
        "paths": paths,
        "source_camera": unit(camera).tolist(),
        "screen_roll_degrees": roll,
    }
    V, E, F, degree, face_size = EXPECTED[name]
    assert (len(vertices), len(edges), len(faces)) == (V, E, F)
    assert V - E + F == 2
    assert all(sum(i in e for e in edges) == degree for i in range(V))
    assert {len(face) for face in faces} == {face_size}
    assert np.allclose(np.linalg.norm(vertices, axis=1), 1.0)
    assert np.allclose(vertices.mean(axis=0), 0.0)
    for face, plane in zip(faces, planes):
        assert np.allclose(vertices[face] @ np.array(plane[:3]), plane[3])
    for path in paths:
        directions = np.array(path["directions"])
        points = directions / gauge(result, directions)[:, None]
        a, b = vertices[path["edge"]]
        expected = a * (1.0 - np.linspace(0, 1, len(points))[:, None]) + b * np.linspace(0, 1, len(points))[:, None]
        assert np.max(np.abs(points - expected)) < 1e-12
    return result


def sphere_geometry():
    # A tilted globe grid, with four meridian great circles and five parallels.
    # The explicit view-space silhouette remains the true circular boundary.
    rotation = camera_matrix([0.45, 0.4, 1.0], 0.0)
    angles = np.linspace(0.0, 2.0 * math.pi, CIRCLE_INTERVALS, endpoint=False)
    paths = []
    for latitude in (-60, -30, 0, 30, 60):
        lat = math.radians(latitude)
        points = np.stack((math.cos(lat) * np.cos(angles),
                           np.full_like(angles, math.sin(lat)),
                           math.cos(lat) * np.sin(angles)), axis=1)
        paths.append({"directions": (points @ rotation.T).tolist(), "closed": True,
                      "role": "grid", "latitude_degrees": latitude})
    for longitude in (0, 45, 90, 135):
        lon = math.radians(longitude)
        points = np.stack((math.cos(lon) * np.cos(angles), np.sin(angles),
                           math.sin(lon) * np.cos(angles)), axis=1)
        paths.append({"directions": (points @ rotation.T).tolist(), "closed": True,
                      "role": "grid", "longitude_degrees": longitude})
    silhouette = np.stack((np.cos(angles), np.sin(angles), np.zeros_like(angles)), axis=1)
    paths.append({"directions": silhouette.tolist(), "closed": True, "role": "silhouette"})
    return {"id": "sphere", "name": "sphere", "label": "Sphere", "kind": "sphere",
            "radius": 1.0, "vertices": [], "faces": [], "planes": [], "edges": [], "paths": paths}


def gauge(shape, directions):
    points = np.asarray(directions, dtype=float)
    if shape["kind"] == "sphere":
        return np.linalg.norm(points, axis=-1)
    planes = np.asarray(shape["planes"])
    return np.max((points @ planes[:, :3].T) / planes[:, 3], axis=-1)


def frontness(shape, directions):
    directions = np.asarray(directions, dtype=float)
    if shape["kind"] == "sphere":
        return unit(directions)[:, 2]
    planes = np.asarray(shape["planes"])
    values = (directions @ planes[:, :3].T) / planes[:, 3]
    active = np.abs(values - values.max(axis=1, keepdims=True)) < 1e-7
    return np.max(np.where(active, planes[:, 2], -10.0), axis=1)


def preview(geometry, directory):
    from PIL import Image, ImageDraw, ImageFont
    directory.mkdir(parents=True, exist_ok=True)
    ss, cell = 3, 340
    image = Image.new("RGB", (cell * 3 * ss, cell * 2 * ss), "black")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18 * ss)
    for index, shape in enumerate(geometry["shapes"]):
        center = np.array([(index % 3 + 0.5) * cell, (index // 3 + 0.46) * cell])
        segments = []
        for path in shape["paths"]:
            directions = np.array(path["directions"])
            if path["closed"]:
                directions = np.vstack((directions, directions[0]))
            points = directions / gauge(shape, directions)[:, None]
            midpoints = unit(directions[:-1] + directions[1:])
            visible = frontness(shape, midpoints) >= -1e-7
            for a, b, show in zip(points[:-1], points[1:], visible):
                xy = np.array([[a[0], -a[1]], [b[0], -b[1]]]) * 117 + center
                segments.append((bool(show), xy))
        for show in (False, True):
            for visible, points in segments:
                if visible != show:
                    continue
                draw.line([tuple(p * ss) for p in points], fill=(210, 240, 255) if show else (30, 34, 38), width=round((2.0 if show else 1.25) * ss))
        draw.text(((center[0] - 95) * ss, (index // 3 * cell + 298) * ss), shape["label"], fill=(210, 210, 210), font=font)
    image.resize((cell * 3, cell * 2), Image.Resampling.LANCZOS).save(directory / "solid-targets.png")


def build():
    shapes = [solid_geometry(name, vertices) for name, vertices in canonical_vertices().items()]
    return {
        "version": 1,
        "projection": {"type": "orthographic", "camera_axis": "+z", "screen_coordinates": ["x", "-y"], "circumradius": 1},
        "morph": {"method": "convex gauge interpolation", "formula": "p(u,t) = u / ((1-t)*gA(u) + t*gB(u))", "edge_intervals": EDGE_INTERVALS},
        "shapes": shapes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("geometry.json"))
    parser.add_argument("--preview-dir", type=Path)
    args = parser.parse_args()
    geometry = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(geometry, separators=(",", ":")) + "\n")
    if args.preview_dir:
        preview(geometry, args.preview_dir)
    print(json.dumps({"path": str(args.output), "bytes": args.output.stat().st_size,
                      "shapes": [{"name": s["name"], "vertices": len(s["vertices"]), "edges": len(s["edges"]), "faces": len(s["faces"]), "paths": len(s["paths"])} for s in geometry["shapes"]]}))


if __name__ == "__main__":
    main()
