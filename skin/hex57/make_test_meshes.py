#!/usr/bin/env python3
"""
Makes three small test meshes in meshes/ so hex57_mesh.py can be tried without Fusion:

    tube.obj         the same 16 in x 8 ft bent tube hex57_layout.py uses, as triangles
    dome.stl         a half sphere 48 in across (binary STL, to test that reader too)
    lumpy_dome.obj   the same dome with bumps and dips, a stand-in for a brain-coral shape

Run:  python3 make_test_meshes.py
"""
import os
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "meshes")


def grid_faces(nu, nt, wrap=True):
    F = []
    for j in range(nt - 1):
        for i in range(nu if wrap else nu - 1):
            a, b = j * nu + i, j * nu + (i + 1) % nu
            c, d = (j + 1) * nu + i, (j + 1) * nu + (i + 1) % nu
            F += [[a, b, d], [a, d, c]]
    return np.array(F)


def write_obj(path, V, F):
    with open(path, "w") as f:
        f.write("# test mesh, inches\n")
        for v in V:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for t in F:
            f.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")


def write_stl(path, V, F):
    with open(path, "wb") as f:
        f.write(b"test mesh, inches".ljust(80, b" "))
        f.write(struct.pack("<I", len(F)))
        for t in F:
            P = V[t]
            n = np.cross(P[1] - P[0], P[2] - P[0])
            n /= np.linalg.norm(n)
            f.write(struct.pack("<12fH", *n, *P.ravel(), 0))


def dome(radius, n_around, n_rings, lumps=0.0):
    """Half sphere (z >= 0), open at the bottom. Ring 0 is the open edge; the last ring is a single pole corner."""
    V = []
    for j in range(n_rings):
        phi = 0.5 * np.pi * j / n_rings                       # angle above the horizontal
        for i in range(n_around):
            th = 2 * np.pi * i / n_around
            flat_base = np.sin(phi) ** 2                          # bumps fade out at the base, so it meets the ground upright
            r = radius * (1 + flat_base * lumps * (np.sin(5 * th + 1.3) * np.sin(6 * phi) * np.cos(phi)
                                                   + 0.5 * np.sin(3 * th) * np.sin(7 * phi)))
            V.append([r * np.cos(phi) * np.cos(th), r * np.cos(phi) * np.sin(th), r * np.sin(phi)])
    V.append([0, 0, radius])
    V = np.array(V)
    F = grid_faces(n_around, n_rings).tolist()
    pole = len(V) - 1
    last = (n_rings - 1) * n_around
    F += [[last + (i + 1) % n_around, last + i, pole] for i in range(n_around)]
    return V, np.array(F)


def tube():
    import hex57_layout as H
    t = H.TestTube()
    nu, nt = 96, 130
    u, tt = np.meshgrid(np.arange(nu) / nu, np.linspace(0, 1, nt))
    tt = H.TUBE_EXTRA / H.TUBE_TOTAL + tt * H.TUBE_LENGTH / H.TUBE_TOTAL      # just the 8 ft, not the test tube's extra length
    V = t.point(u, tt).reshape(-1, 3)
    return V, grid_faces(nu, nt)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write_obj(os.path.join(OUT, "tube.obj"), *tube())
    write_stl(os.path.join(OUT, "dome.stl"), *dome(24.0, 72, 36))
    write_obj(os.path.join(OUT, "lumpy_dome.obj"), *dome(24.0, 72, 36, lumps=0.10))
    for f in sorted(os.listdir(OUT)):
        print(f, f"{os.path.getsize(os.path.join(OUT, f)) / 1e6:.2f} MB")
