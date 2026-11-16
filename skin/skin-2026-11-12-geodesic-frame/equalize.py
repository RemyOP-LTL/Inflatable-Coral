#!/usr/bin/env python3
"""
Make every spoke the same length (Remy's rule, 2026-11-15).

Takes a layout.json from hex57_mesh.py and nudges the nodes, keeping them on the surface, until
  - every spoke (every polygon edge that is not a side of a pentagon plate) has the same length L, and
  - every pentagon plate stays a regular pentagon of one size.
L is the average spoke length of the layout you give it, unless you pass --length.

Run:  python3 equalize.py layouts/tube-edge5/layout.json --out layouts/tube-equal5
(needs numpy and scipy; reads the mesh named in the layout from ../hex57/meshes/)
"""
import argparse, json, math, os, sys
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hex57"))
import hex57_mesh as M                                           # noqa: E402


class Surface:
    """Snap points back onto the mesh (nearest sample, then onto its triangle's plane)."""
    def __init__(self, mesh_path, units="in"):
        V, F = (M.read_stl if mesh_path.lower().endswith(".stl") else M.read_obj)(mesh_path)
        V = V * M.UNITS[units]
        P = V[F]; cr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        area = 0.5 * np.linalg.norm(cr, axis=1); n = cr / np.maximum(2 * area, 1e-12)[:, None]
        rng = np.random.default_rng(1)
        k = np.maximum(1, np.round(area * 12).astype(int))
        face = np.repeat(np.arange(len(F)), k)
        r1, r2 = rng.random(len(face)), rng.random(len(face)); f = r1 + r2 > 1; r1[f], r2[f] = 1 - r1[f], 1 - r2[f]
        w = np.stack([1 - r1 - r2, r1, r2], 1)
        self.pts, self.nrm = (P[face] * w[..., None]).sum(1), n[face]
        self.tree = cKDTree(self.pts)

    def snap(self, X):
        _, i = self.tree.query(X)
        p, n = self.pts[i], self.nrm[i]
        return X - ((X - p) * n).sum(1)[:, None] * n


def equalize(layout, mesh_path, length=None, iters=600, plate_scale=1.0, log=print, anchor=0.05, lam=3.0, round_w=0.5, tree_w=0.3, band_w=30.0):
    V = np.array(layout["vertices"], float)
    polys = layout["polygons"]
    surf = Surface(mesh_path)
    plate_edges, spoke_edges, plate_pairs = set(), set(), []
    lost = set((layout.get("partition") or {}).get("lost", ()))        # pentagons on the spine are windows, not plates
    is_plate = [len(p) == 5 and i not in lost for i, p in enumerate(polys)]
    for p in [q for q, ok in zip(polys, is_plate) if ok]:
        if True:
            for a, b in zip(p, p[1:] + p[:1]):
                plate_edges.add(frozenset((a, b)))
    for p in polys:
        for a, b in zip(p, p[1:] + p[:1]):
            e = frozenset((a, b))
            if e not in plate_edges:
                spoke_edges.add(e)
    part = layout.get("partition")
    if part:                                                     # Remy: only the LOOSE spokes must be equal
        S = np.array([sorted(e) for e in part["loose"]])
        T_ = np.array([sorted(e) for e in list(part["tree"])]).reshape(-1, 2)
    else:                                                        # every spoke equal
        S = np.array([sorted(e) for e in spoke_edges]); T_ = np.zeros((0, 2), int)
    L0 = np.linalg.norm(V[S[:, 0]] - V[S[:, 1]], axis=1)
    L = float(length or L0.mean())
    Lt = float(np.linalg.norm(V[T_[:, 0]] - V[T_[:, 1]], axis=1).mean()) if len(T_) else L
    pent = [q for q, ok in zip(polys, is_plate) if ok]
    sp0 = np.mean([np.linalg.norm(V[a] - V[b]) for p in pent for a, b in zip(p, p[1:] + p[:1])]) * plate_scale
    phi = (1 + 5 ** 0.5) / 2
    A, B, T, W = [], [], [], []
    for a, b in S:
        A.append(a); B.append(b); T.append(L); W.append(1.0)
    for a, b in T_:                                                  # attached spokes: only a gentle pull toward their own average
        A.append(a); B.append(b); T.append(Lt); W.append(tree_w)
    for p in pent:                                             # regular pentagon: 5 sides + 5 diagonals
        for i in range(5):
            A.append(p[i]); B.append(p[(i + 1) % 5]); T.append(sp0); W.append(1.0)
            A.append(p[i]); B.append(p[(i + 2) % 5]); T.append(sp0 * phi); W.append(1.0)
    band = np.array(sorted((part or {}).get("band", [])), int)
    for p, plate_ in zip(polys, is_plate):                     # windows: second-nearest corners at the regular-polygon distance
        k = len(p)
        if plate_ or (part and any(v in set(band.tolist()) for v in p)):     # plates, and partial windows cut by the spine
            continue
        al = math.pi * (k - 2) / k
        for i in range(k):
            A.append(p[i]); B.append(p[(i + 2) % k]); T.append(2 * (L if part is None else (L + Lt) / 2) * math.sin(al / 2)); W.append(round_w)
    A, B, T, W = np.array(A), np.array(B), np.array(T), np.array(W)
    n = len(V)
    start = V.copy()
    from scipy.optimize import least_squares
    from scipy.sparse import lil_matrix
    # unknowns: every node's x, y, z.  residuals: (length - target) for every spoke/plate constraint, plus
    # how far each node sits off the surface (nearest surface point and its plane, refreshed each round).
    rows = len(A)
    nb_ = len(((layout.get('partition') or {}).get('band', [])))
    pat = lil_matrix((rows + 2 * n + nb_, 3 * n), dtype=int)
    for r, (a_, b_) in enumerate(zip(A, B)):
        pat[r, 3 * a_:3 * a_ + 3] = 1; pat[r, 3 * b_:3 * b_ + 3] = 1
    for i in range(n):
        pat[rows + i, 3 * i:3 * i + 3] = 1
        pat[rows + n + i, 3 * i:3 * i + 3] = 1
    for k, b_ in enumerate(band):
        pat[rows + 2 * n + k, 3 * b_:3 * b_ + 3] = 1
    X0 = start.copy()
    for rnd in range(12):
        _, k = surf.tree.query(V); P0, N0 = surf.pts[k], surf.nrm[k]
        onmesh = (np.linalg.norm(V - P0, axis=1) < 1.5).astype(float)       # nodes in the extra rows past the open edges are not on the mesh: leave them free
        def res(x):
            X = x.reshape(-1, 3)
            return np.concatenate([(np.linalg.norm(X[B] - X[A], axis=1) - T) * W, lam * onmesh * ((X - P0) * N0).sum(1), anchor * np.linalg.norm(X - X0, axis=1), band_w * np.linalg.norm(X[band] - X0[band], axis=1)])
        sol = least_squares(res, V.ravel(), jac_sparsity=pat.tocsr(), method="trf", max_nfev=25)
        V = sol.x.reshape(-1, 3)
        V = np.where((np.linalg.norm(V - P0, axis=1) < 1.5)[:, None], surf.snap(V), V) if rnd == 11 else V
        sl = np.linalg.norm(V[S[:, 0]] - V[S[:, 1]], axis=1)
        log(f"  round {rnd + 1:2d}: spoke length {sl.mean():.3f} in, spread {sl.std() / sl.mean() * 100:.2f} %, min {sl.min():.2f}, max {sl.max():.2f}")
    sl = np.linalg.norm(V[S[:, 0]] - V[S[:, 1]], axis=1)
    ps = np.array([np.linalg.norm(V[a] - V[b]) for p in pent for a, b in zip(p, p[1:] + p[:1])])
    moved = np.linalg.norm(V - start, axis=1)
    out = dict(layout)
    out["vertices"] = np.round(V, 4).tolist()
    info = []
    for p, i in zip(polys, layout["polygon_info"]):
        j = dict(i); P = V[p]; j["centre"] = np.round(P.mean(0), 4).tolist()
        j.pop("cut", None); info.append(j)
    out["polygon_info"] = info
    out["equalized"] = dict(spoke_length=L, spoke_std_pct=float(sl.std() / sl.mean() * 100), spoke_min=float(sl.min()),
                            spoke_max=float(sl.max()), plate_side=float(ps.mean()), plate_side_std_pct=float(ps.std() / ps.mean() * 100),
                            node_moved_mean=float(moved.mean()), node_moved_max=float(moved.max()), spokes=int(len(S)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout"); ap.add_argument("--out", required=True)
    ap.add_argument("--length", type=float, help="spoke length in inches (default: the layout's average)")
    ap.add_argument("--iters", type=int, default=600)
    ap.add_argument("--anchor", type=float, default=0.05, help="how strongly nodes are held near where they started")
    ap.add_argument("--round", type=float, default=0.5, help="how strongly cells are pulled toward regular polygons")
    ap.add_argument("--lam", type=float, default=3.0, help="how strongly nodes are held on the surface")
    a = ap.parse_args()
    lay = json.load(open(a.layout))
    mesh = os.path.join(os.path.dirname(HERE), "hex57", "meshes", os.path.basename(lay["params"]["MESH_FILE"]))
    res = equalize(lay, mesh, a.length, a.iters, anchor=a.anchor, lam=a.lam, round_w=a.round)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "layout.json"), "w"))
    print(json.dumps(res["equalized"], indent=1))


if __name__ == "__main__":
    main()
