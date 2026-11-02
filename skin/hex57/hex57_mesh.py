#!/usr/bin/env python3
"""
Layout B on ANY surface: read a mesh file (OBJ or STL) and lay the hexagon / pentagon / heptagon
skin over it.

    python3 hex57_mesh.py meshes/dome.obj
    python3 hex57_mesh.py my_branch.stl --units mm --edge 3 --out my_branch_layout

What it does, in plain language:
  1. Reads the mesh (a surface made of triangles, such as an export from Fusion 360) and checks it:
     one connected surface, triangles all facing the same way, outward.
  2. Finds the open edges of the surface (the rim of a dome, the ends of a tube). Shapes touching an
     open edge are cut off there, drawn green and left out of the counts.
  3. Uses the mesh's own triangles as the starting point, then hands over to the same code that
     hex57_layout.py uses on the test tube: adapt the pattern to the shape size, add pentagon /
     heptagon pairs, relax the corners, measure and write the files.

Nothing in the pattern code knows about tubes any more; only hex57_layout.py's own test tube does.

Writes into the output folder (default: layouts/<mesh name>/ next to this file):
    layout.json, coverage/layout_*.json, viewer.html (open it in a browser), preview_3d.png
"""
import argparse
import json
import math
import os
import struct
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = {"in": 1.0, "mm": 1 / 25.4, "cm": 1 / 2.54, "m": 1 / 0.0254, "ft": 12.0}


# ============================================================================
# 1. Reading and checking the mesh
# ============================================================================
def read_obj(path):
    V, F = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                V.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("f "):
                idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
                idx = [i - 1 if i > 0 else len(V) + i for i in idx]   # OBJ counts from 1; negatives count back
                for k in range(1, len(idx) - 1):                      # quads and bigger faces -> triangle fan
                    F.append([idx[0], idx[k], idx[k + 1]])
    return np.array(V, float), np.array(F, int)


def read_stl(path):
    data = open(path, "rb").read()
    n_tri = struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else -1
    if len(data) == 84 + 50 * n_tri:                                  # binary STL
        rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                            count=n_tri, offset=84)
        tri = rec["v"].astype(float).reshape(-1, 3)
    else:                                                             # ASCII STL
        tri = np.array([[float(x) for x in ln.split()[1:4]]
                        for ln in data.decode("ascii", "ignore").splitlines() if ln.strip().startswith("vertex")])
    return tri, np.arange(len(tri)).reshape(-1, 3)


def weld(V, F, tol):
    """Merge corners that sit at the same place (STL stores every triangle on its own)."""
    key = np.round(V / tol).astype(np.int64)
    _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V, F = V[first], inverse.reshape(-1)[F]
    keep = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])      # drop collapsed triangles
    return V, F[keep]


def orient_and_clean(V, F, flip):
    """Keep the largest connected piece, make all triangles wind the same way, then point them outward."""
    edge_faces = defaultdict(list)
    for fi, f in enumerate(F):
        for k in range(3):
            a, b = int(f[k]), int(f[(k + 1) % 3])
            edge_faces[(min(a, b), max(a, b))].append(fi)
    bad = [e for e, fs in edge_faces.items() if len(fs) > 2]
    if bad:
        raise SystemExit(f"The mesh has {len(bad)} edges shared by more than two triangles (a non-manifold "
                         "surface). Export a single clean surface body and try again.")
    F = F.copy()
    comp = -np.ones(len(F), int)
    n_comp = 0
    for start in range(len(F)):
        if comp[start] >= 0:
            continue
        comp[start] = n_comp
        stack = [start]
        while stack:
            fi = stack.pop()
            for k in range(3):
                a, b = int(F[fi][k]), int(F[fi][(k + 1) % 3])
                for gi in edge_faces[(min(a, b), max(a, b))]:
                    if gi == fi:
                        continue
                    # A neighbour that winds the same way along this edge has to be turned around.
                    same = any((int(F[gi][j]), int(F[gi][(j + 1) % 3])) == (a, b) for j in range(3))
                    if comp[gi] < 0:
                        if same:
                            F[gi] = F[gi][[0, 2, 1]]
                        comp[gi] = n_comp
                        stack.append(gi)
                    elif same:
                        raise SystemExit("The mesh can't be given one consistent facing (like a Möbius strip, "
                                         "or two sheets glued wrongly). Export a cleaner surface.")
        n_comp += 1
    if n_comp > 1:
        sizes = np.bincount(comp)
        print(f"  note: the file holds {n_comp} separate pieces; using the biggest ({sizes.max()} triangles)")
        F = F[comp == sizes.argmax()]
    used = np.unique(F)
    V, F = V[used], np.searchsorted(used, F)
    # Outward: triangle normals should mostly point away from the middle of the shape.
    P = V[F]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    away = ((P.mean(1) - V.mean(0)) * n).sum(1).sum()
    if (away < 0) != flip:
        F = F[:, [0, 2, 1]]
        print("  note: triangles were facing inward, so they were turned around" if not flip else
              "  note: triangles turned around, as --flip asked")
    elif flip:
        print("  note: --flip made no change needed (already pointing the other way)")
    return V, F


def vertex_normals(V, F):
    P = V[F]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])         # length = 2 x area, so big triangles count more
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], n)
    return N / np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]


def boundary_loops(F):
    """The open edges of the surface as closed loops of corner numbers."""
    count = defaultdict(int)
    nxt = defaultdict(list)
    for f in F:
        for k in range(3):
            a, b = int(f[k]), int(f[(k + 1) % 3])
            count[(min(a, b), max(a, b))] += 1
    for f in F:
        for k in range(3):
            a, b = int(f[k]), int(f[(k + 1) % 3])
            if count[(min(a, b), max(a, b))] == 1:
                nxt[a].append(b)
    if any(len(v) > 1 for v in nxt.values()):
        raise SystemExit("An open edge of the mesh touches itself at a single point (a pinch). "
                         "Export a surface whose boundary is a clean loop.")
    loops, seen = [], set()
    for start in nxt:
        if start in seen:
            continue
        loop, v = [], start
        while v not in seen:
            seen.add(v)
            loop.append(v)
            v = nxt[v][0]
        loops.append(loop)
    return loops


def resample_loop(P, step):
    """A closed loop of points -> a dense polyline (about `step` apart) used to snap shapes to the rim."""
    Q = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], step)
    return np.stack([np.interp(t, s, Q[:, k]) for k in range(3)], 1)


def dense_sample(V, F, N, rng, max_points=300_000, density=40.0):
    """Random points over the triangles, each with an outward direction. The rest of the code only
    uses this cloud of points (it never looks at the triangles again)."""
    P = V[F]
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    density = min(density, max_points / area.sum())
    want = area * density
    k = np.floor(want).astype(int) + (rng.random(len(F)) < want - np.floor(want))
    face = np.repeat(np.arange(len(F)), k)
    r1, r2 = rng.random(len(face)), rng.random(len(face))
    flip = r1 + r2 > 1
    r1[flip], r2[flip] = 1 - r1[flip], 1 - r2[flip]
    w = np.stack([1 - r1 - r2, r1, r2], 1)
    pts = (P[face] * w[..., None]).sum(1)
    nrm = (N[F[face]] * w[..., None]).sum(1)
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    return pts, nrm, float(area.sum())


class WholeSurface:
    """Stands in for hex57_layout.Region: every point of the mesh counts (the tube's 'extra length past
    the 8 ft' has no meaning here; shapes at an open edge are cut off and left out anyway)."""

    def __init__(self, area):
        self.area = area

    def inside(self, X):
        return np.ones(len(np.atleast_2d(X)), bool)


# ============================================================================
# 2. Running the layout
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", help="OBJ or STL file (a surface made of triangles)")
    ap.add_argument("--units", choices=sorted(UNITS), default="in", help="units the file is in (default in)")
    ap.add_argument("--edge", type=float, help="hexagon side length in inches (default 3.0)")
    ap.add_argument("--flip", action="store_true", help="turn triangles the other way if 'outward' came out wrong")
    ap.add_argument("--pent-ratio", type=float, help="pentagon side as a multiple of --edge (default 1.15)")
    ap.add_argument("--coverage", type=float, help="target share of area covered by pentagons, 0.10 to 0.30 (default 0.25)")
    ap.add_argument("--hole-rim", type=float, help="plastic left around the polyp hole, inches (default 0.5)")
    ap.add_argument("--seed", type=int, help="random seed (default 7)")
    ap.add_argument("--out", help="output folder (default layouts/<mesh name>/)")
    args = ap.parse_args()
    # These settings are read when hex57_layout is imported, so set them first.
    for var, val in (("HEX57_EDGE", args.edge), ("HEX57_PENT_RATIO", args.pent_ratio), ("HEX57_COVERAGE", args.coverage),
                     ("HEX57_HOLE_RIM", args.hole_rim), ("HEX57_SEED", args.seed)):
        if val is not None:
            os.environ[var] = str(val)
    import hex57_layout as H                             # noqa: E402  (after the environment is set)

    name = os.path.splitext(os.path.basename(args.mesh))[0]
    out_dir = args.out or os.path.join(HERE, "layouts", name)
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(H.SEED)

    print(f"reading {args.mesh}")
    V, F = read_stl(args.mesh) if args.mesh.lower().endswith(".stl") else read_obj(args.mesh)
    if len(F) == 0:
        raise SystemExit(f"No triangles found in {os.path.basename(args.mesh)}. It needs to be an OBJ or STL "
                         "mesh of a surface (in Fusion: right-click the body, Save As Mesh).")
    V = V * UNITS[args.units]
    V, F = weld(V, F, 1e-4)
    V, F = orient_and_clean(V, F, args.flip)
    N = vertex_normals(V, F)
    loops = boundary_loops(F)
    lo, hi = V.min(0), V.max(0)
    print(f"  {len(V)} corners, {len(F)} triangles, size {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} x "
          f"{hi[2] - lo[2]:.1f} in, {len(loops)} open edge(s)")

    pts, nrm, area = dense_sample(V, F, N, rng)
    surf = H.Surface(pts, nrm, [resample_loop(V[l], 0.1) for l in loops])
    size = H.SizeField(surf, area, rng)

    rim = -np.ones(len(V), int)
    for k, l in enumerate(loops):
        rim[l] = k
    mesh = H.SeedMesh(V, F.tolist(), rim.tolist(), surf)
    bad = [t for t in mesh.T if not mesh.tri_ok(*t)]
    if bad:
        print(f"  warning: {len(bad)} triangles fold sharply against the surface direction; "
              "if the layout looks wrong try --flip or a smoother mesh")
    mesh.region = WholeSurface(area)

    # The input triangles are not the size we want. Bring them close first so the main loop starts sane.
    for _ in range(30):
        n0 = len(mesh.V)
        H.split_long(mesh, size)
        H.collapse_short(mesh, size)
        if abs(len(mesh.V) - n0) < 0.01 * n0:
            break
    mesh.compact()

    def render_fn(C, polys, info, m):
        render_views(H, C, polys, info, m, name, out_dir)
        return None

    params = dict(SURFACE=f"{name} ({len(loops)} open edge(s), {area:.0f} sq in)", MESH_FILE=os.path.basename(args.mesh))
    H.run_layout(mesh, surf, size, rng, out_dir, render_fn, params)


def render_views(H, C, polys, info, metrics, name, out_dir):
    """Three pictures of the whole skin from the side, above and below. The longest direction of the
    shape is turned to run left-right, so long shapes (a tube) fill the picture."""
    import matplotlib.pyplot as plt
    Cv, R = H.tube_axes_view(C)                        # long direction -> z
    Cv = Cv[:, [2, 0, 1]]                              # ... then -> x (left-right)
    info_v = [dict(d, normal=(R @ d["normal"])[[2, 0, 1]]) for d in info]
    lo, hi = Cv.min(0) - 0.5, Cv.max(0) + 0.5
    half = 0.5 * float(max(hi - lo))                   # a cube around the shape so no view is clipped
    mid = 0.5 * (hi + lo)
    lo, hi = mid - half, mid + half
    fig = plt.figure(figsize=(16, 6))
    for k, (elev, azim, title) in enumerate([(10, -90, "side"), (55, -60, "from above"), (-35, 120, "from below")]):
        ax = fig.add_axes([k / 3, 0.08, 1 / 3, 0.82], projection="3d")
        H.draw_3d(ax, Cv, polys, info_v, elev, azim, lo, hi, zoom=1.15)
        ax.set_title(title, fontsize=12, color="#444", y=0.97)
    fig.legend(handles=H.legend_handles(metrics), loc="lower center", ncol=5, frameon=False, fontsize=11)
    fig.suptitle(f"Layout B on {name}: {100 * metrics['pentagon_coverage']:.0f} % pentagons", fontsize=14)
    fig.savefig(os.path.join(out_dir, "preview_3d.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main()
