#!/usr/bin/env python3
"""
Layout -> finished skin layout. One command for the whole chain.

With the spine (the bent tube stood up as a smile):
  0. the spine is a curve stored in the surface file (spinecurve.py); no curve, no spine
  1. clip_spine.py   the spine comes first: cut the pattern by the spine strip, so no spoke lies on or crosses it
  2. partition.py    pentagon + its five corner spokes = one part; spokes off the spine's edge = spine spokes; the rest are loose
  3. equalize.py     make the loose spokes one length
  4. spine.py        stand the tube up as a smile and describe the spine piece
Without a spine (dome, an uploaded surface): steps 2 and 3 only (`build_plain`).

Run:  python3 build_smile.py layouts/_sources/tube-clear5/layout.json --out layouts/smile-tube
      python3 build_smile.py layouts/_sources/dome-edge5/layout.json --out layouts/dome-equal5 --no-spine
"""
import argparse, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import equalize, partition                                              # noqa: E402


def _loose_report(res):
    V = np.array(res["vertices"]); loose = np.array(res["partition"]["loose"]).reshape(-1, 2)
    L = np.linalg.norm(V[loose[:, 0]] - V[loose[:, 1]], axis=1)
    return dict(loose_spokes=int(len(loose)), loose_mean=float(L.mean()), loose_min=float(L.min()), loose_max=float(L.max()),
                loose_spread_pct=float(L.std() / L.mean() * 100), arm_spokes=len(res["partition"]["tree"]),
                parts=len(res["partition"]["plates"]), spine_spokes=len(res["partition"].get("spine_spokes", [])))


def load_curve(mesh_path):
    """The spine curve stored in the surface file, as a SpineCurve, or None."""
    import spinecurve
    pts = spinecurve.read_curve(mesh_path)
    return spinecurve.SpineCurve(pts, equalize.Surface(mesh_path)) if pts is not None else None


def drop_extension(layout):
    """Ignore the extra rows past the open edges of the surface (Remy, 2026-11-16): keep only the shapes on the surface. Spokes along
    the edge simply end at their nodes with their usual ends."""
    info = layout["polygon_info"]
    keep = [i for i, x in enumerate(info) if not x.get("end")]
    used = sorted({v for i in keep for v in layout["polygons"][i]})
    remap = {v: i for i, v in enumerate(used)}
    res = dict(layout)
    res["vertices"] = [layout["vertices"][v] for v in used]
    res["polygons"] = [[remap[v] for v in layout["polygons"][i]] for i in keep]
    res["polygon_info"] = [info[i] for i in keep]
    return res


def build(layout, mesh_path, width=4.0, log=print):
    import clip_spine, spine
    layout = drop_extension(layout)
    curve = load_curve(mesh_path)
    if curve is None:
        return build_plain(layout, mesh_path, log)
    lay, _ = clip_spine.clip(layout, curve, width)
    lay["partition"] = partition.partition(lay, lay["clip"]["band"], lay["clip"].get("edge", ()))
    eq = equalize.equalize(lay, mesh_path, anchor=0.02, round_w=0.05, tree_w=0.1, log=lambda *a: None)
    res, rep = spine.make(eq, curve, width)
    rep.update(_loose_report(res))
    res["equalized"] = dict(eq["equalized"], **{k: rep[k] for k in ("loose_mean", "loose_min", "loose_max", "loose_spread_pct")})
    return res, rep


def build_plain(layout, mesh_path, log=print):
    layout = drop_extension(layout) if any(x.get('end') for x in layout['polygon_info']) else layout
    lay = dict(layout, partition=partition.partition(layout, ()))
    eq = equalize.equalize(lay, mesh_path, anchor=0.02, round_w=0.05, tree_w=0.1, log=lambda *a: None)
    rep = _loose_report(eq)
    eq["equalized"] = dict(eq["equalized"], **{k: rep[k] for k in ("loose_mean", "loose_min", "loose_max", "loose_spread_pct")})
    return eq, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout"); ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=float, default=4.0)
    ap.add_argument("--no-spine", action="store_true")
    ap.add_argument("--mesh", help="mesh file (default: looked up in ../hex57/meshes, then ../hex57/uploads)")
    a = ap.parse_args()
    lay = json.load(open(a.layout))
    name = os.path.basename(lay["params"]["MESH_FILE"])
    mesh = a.mesh or next(p for p in (os.path.join(HERE, "shapes", name), os.path.join(HERE, "shapes", "uploads", name)) if os.path.isfile(p))
    res, rep = (build_plain(lay, mesh) if a.no_spine else build(lay, mesh, a.width))
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "layout.json"), "w"))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
