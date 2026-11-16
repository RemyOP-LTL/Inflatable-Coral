"""Write the inflated polyp as a "polyp bundle" (polyp.json) for the workbench.

What it does: runs the same inflated simulation as the polyp tool, then saves the 3D surface
in the polyp's own coordinates: origin at the centre of the cuff bottom (the ring that meets the
skin), +z pointing straight out of the skin. The workbench uses this to put one polyp on each
pentagon. The format is described in shared/FORMATS.md.

Run:  python3 export_bundle.py --out bundles/polyp-5-taper-tabs     (about 1 minute)
This file only reads the existing code (make_pattern.py, sim_polyp.py); it changes nothing there.
"""
import argparse, json, os
import numpy as np
import make_pattern as P
import sim_polyp as S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="folder to write polyp.json into")
    ap.add_argument("--name", default="polyp-5-taper-tabs")
    ap.add_argument("--iters", type=int, default=6000)
    a = ap.parse_args()

    m = S.build(single=True)
    X = S.relax(m, iters=a.iters)
    m, X = S.replicate(m, X)
    X = np.asarray(X, float) + np.array([0, 0, P.CUFF_HEIGHT])   # cuff bottom -> z = 0
    F = np.asarray(m["F"], int)
    ring = X[X[:, 2] < 0.05]
    out = {
        "format": "coral-polyp-bundle", "version": 1, "name": a.name, "units": "inch",
        "frame": "origin = centre of the cuff bottom (meets the skin); +z = straight out of the skin",
        "mesh": {"vertices": np.round(X, 3).tolist(), "triangles": F.tolist()},
        "size": {
            "tube_diameter": P.TUBE_DIAMETER,
            "footprint_diameter": round(float(2 * np.linalg.norm(ring[:, :2], axis=1).max()), 3),
            "height": round(float(X[:, 2].max()), 3),
            "reach_radius": round(float(np.linalg.norm(X[:, :2], axis=1).max()), 3),
        },
        "settings": {"fingers": P.THUMBS, "finger_length": P.THUMB_LENGTH, "cuff_height": P.CUFF_HEIGHT,
                     "scale": P.SCALE, "sim": "inflated, single finger replicated"},
        "pattern": {"files": ["../../designs/polyp-5-taper-tabs-pattern.pdf"]},
    }
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "polyp.json")
    json.dump(out, open(path, "w"), separators=(",", ":"))
    print(path, len(X), "points,", len(F), "triangles,", out["size"])


if __name__ == "__main__":
    main()
