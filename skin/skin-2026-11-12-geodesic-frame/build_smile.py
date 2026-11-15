#!/usr/bin/env python3
"""
Layout -> smile tube with a spine, loose spokes equalised. One command for the whole chain:

  1. find the nodes that fall inside the spine (plus a small margin for the bumps)
  2. split the spokes into attached (a tree out of every plate) and loose (partition.py)
  3. make the loose spokes one length (equalize.py)
  4. stand the tube up as a smile and lay the spine (spine.py)

Run:  python3 build_smile.py layouts/_sources/tube-edge5/layout.json --out layouts/smile-tube
"""
import argparse, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import equalize, partition, spine                                   # noqa: E402


def build(layout, mesh_path, width=4.0, margin=0.75, log=print):
    V0 = np.array(layout["vertices"], float)
    u = np.array([spine.station(p)[2] for p in V0])
    band = [int(v) for v in np.where(np.abs(u) < width / 2 + margin)[0]]
    layout = dict(layout, partition=partition.partition(layout, band))
    eq = equalize.equalize(layout, mesh_path, anchor=0.05, round_w=0.1, tree_w=0.3, log=lambda *a: None)
    res, rep = spine.make(eq, width)
    V = np.array(res["vertices"]); loose = np.array(res["partition"]["loose"])
    L = np.linalg.norm(V[loose[:, 0]] - V[loose[:, 1]], axis=1)
    rep.update(loose_spokes=int(len(loose)), loose_mean=float(L.mean()), loose_min=float(L.min()), loose_max=float(L.max()),
               loose_spread_pct=float(L.std() / L.mean() * 100), tree_spokes=len(res["partition"]["tree"]))
    res["equalized"] = dict(eq["equalized"], loose_mean=rep["loose_mean"], loose_min=rep["loose_min"], loose_max=rep["loose_max"], loose_spread_pct=rep["loose_spread_pct"])
    return res, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout"); ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=float, default=4.0)
    a = ap.parse_args()
    lay = json.load(open(a.layout))
    mesh = os.path.join(os.path.dirname(HERE), "hex57", "meshes", os.path.basename(lay["params"]["MESH_FILE"]))
    res, rep = build(lay, mesh, a.width)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "layout.json"), "w"))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
