#!/usr/bin/env python3
"""
Layout built AROUND the spine: the same hex57 layout, but no new pentagon may be placed where its plate would touch
the spine. (The only change to hex57's method is one extra test in add_pair; everything else is hex57 unchanged.)

Run:  python3 spine_layout.py ../hex57/meshes/tube.obj --edge 5 --out layouts/_sources/tube-clear5
Takes about 40 s. Then:  python3 build_smile.py layouts/_sources/tube-clear5/layout.json --out layouts/smile-tube-clear
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
HEX = os.path.join(os.path.dirname(HERE), "hex57")
sys.path.insert(0, HEX); sys.path.insert(0, HERE)
# hex57 reads its settings from the environment when it is first imported, so set them before importing anything that imports it
for flag, var in (("--edge", "HEX57_EDGE"), ("--pent-ratio", "HEX57_PENT_RATIO"), ("--coverage", "HEX57_COVERAGE"),
                  ("--hole-rim", "HEX57_HOLE_RIM"), ("--seed", "HEX57_SEED"), ("--hole-diameter", "HEX57_HOLE_DIAMETER")):
    if flag in sys.argv:
        os.environ[var] = sys.argv[sys.argv.index(flag) + 1]
import hex57_layout as H                                          # noqa: E402
import hex57_mesh as M                                            # noqa: E402
import spine                                                      # noqa: E402

KEEP_OUT = float(os.environ.get("SPINE_KEEP_OUT", 2.0 + 0.75 + 5.0 + 0.3))     # spine half width + bump margin + pentagon radius + slack


def too_close(p):
    return abs(spine.station(np.asarray(p))[2]) < KEEP_OUT


def add_pair(mesh, rng, size, min_angle):
    """hex57_layout.add_pair, plus: a new pentagon may not be seeded near the spine."""
    edges = list(mesh.edge_tris.keys())
    rng.shuffle(edges)
    pent_pos = {v: mesh.V[v] for v in range(len(mesh.V)) if mesh.is_pentagon(v)}
    best, best_d, tried = None, -1.0, 0
    for e in edges:
        info = mesh.flip_info(e)
        if info is None:
            continue
        p, q, c, d, _ = info
        if any(mesh.rim[v] >= 0 for v in (p, q, c, d)):
            continue
        val = {v: mesh.valence(v) for v in (p, q, c, d)}
        if any(val[v] not in (6, 7) for v in (p, q)) or any(val[v] not in (5, 6) for v in (c, d)):
            continue
        new5 = [v for v in (p, q) if val[v] == 6]
        lost5 = [v for v in (c, d) if val[v] == 5]
        if len(new5) <= len(lost5):
            continue
        if any(too_close(mesh.V[v]) for v in new5):                  # <- the one addition
            continue
        after5 = (set(pent_pos) - set(lost5)) | set(new5)
        nb = {v: set(mesh.nbrs[v]) for v in (p, q, c, d)}
        nb[p].discard(q); nb[q].discard(p); nb[c].add(d); nb[d].add(c)
        if any(w in after5 for v in new5 for w in nb[v]):
            continue
        if not (mesh.tri_ok(c, p, d, min_angle=min_angle) and mesh.tri_ok(d, q, c, min_angle=min_angle)):
            continue
        others = [pos for v, pos in pent_pos.items() if v not in lost5]
        dist = min(np.linalg.norm(np.array(others) - mesh.V[v], axis=1).min() for v in new5) if others else 1e9
        score = min(dist, 12.0) / 12.0 + size.across(mesh.V[p])[0] / H.SIZE_MAX
        if score > best_d:
            best, best_d = info, score
        tried += 1
        if tried >= H.PICK_FROM:
            break
    if best is None:
        return False
    mesh.flip(best)
    mesh.rebuild()
    return True


if __name__ == "__main__":
    H.add_pair = add_pair
    sys.argv[0] = "hex57_mesh.py"
    M.main()
