#!/usr/bin/env python3
"""
The smile tube with a spine (Remy, 2026-11-15).

1. Stands the bent test tube up so its bend is a smile seen from the front: the middle of the tube
   touches the ground plane (z = 0, Fusion's "Top" plane) and both ends curve up.
2. Lays a solid SPINE, 4 in wide, along the top line on the inside of the curve.
3. Nodes that fall inside the spine are dropped; every spoke that ran into the spine now ends on it, at a
   rivet hole with a round bump on the spine edge. Pentagon plates that touch the spine are dropped.

TUBE-SPECIFIC (like hex57's TestTube): it knows the tube is a circular arc (BEND_RADIUS) of radius TUBE_RADIUS.

Run:  python3 spine.py layouts/tube-equal5/layout.json --out layouts/smile-tube
"""
import argparse, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hex57"))
import hex57_layout as H                                          # noqa: E402  (only used for the tube's size constants)

R, r = float(H.BEND_RADIUS), float(H.TUBE_RADIUS)
C = np.array([R, 0.0, 0.0])                                       # centre of the bend, axis along y
A_LO = H.TUBE_EXTRA / R                                           # station angle where the 8 ft of tube starts
A_HI = (H.TUBE_EXTRA + H.TUBE_LENGTH) / R
A_MID = (A_LO + A_HI) / 2


def station(p):
    """(a, theta, u, sigma) of a point on the tube: a = how far along the bend, theta = angle round the tube
    (pi = the inside of the bend), u = distance across from the inside line, sigma = distance along it."""
    q = p - C
    a = math.atan2(q[2], -q[0])
    rho = math.hypot(q[0], q[2])
    th = math.atan2(-p[1], rho - R)
    d = (th - math.pi + math.pi) % (2 * math.pi) - math.pi        # theta - pi, wrapped to -pi..pi
    return a, th, r * d, (R - r) * (a - A_LO)


def smile(P):
    """Rigid move: bend plane becomes vertical, inside of the bend up, lowest point on z = 0."""
    a = A_MID
    c_mid = np.array([R * (1 - math.cos(a)), 0.0, R * math.sin(a)])
    X = np.array([math.sin(a), 0.0, math.cos(a)])
    Z = np.array([math.cos(a), 0.0, -math.sin(a)])
    Y = np.cross(Z, X)
    Q = (np.atleast_2d(P) - c_mid)
    return np.stack([Q @ X, Q @ Y, Q @ Z + r], 1)


def make(layout, width=4.0, bump_radius=1.0, hole=0.25):
    V0 = np.array(layout["vertices"], float)
    st = np.array([station(p) for p in V0])
    u = st[:, 2]
    inband = np.abs(u) < width / 2
    if layout.get("partition") and layout["partition"].get("band") is not None:       # the nodes the partition treated as spine
        inband = np.zeros(len(V0), bool); inband[layout["partition"]["band"]] = True
    polys = layout["polygons"]
    adj = {}
    for p in polys:
        for a, b in zip(p, p[1:] + p[:1]):
            adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
    conn = sorted(v for v in np.where(inband)[0] if any(not inband[w] for w in adj.get(v, ())))
    V = smile(V0)
    info = []
    dropped_pent = 0
    for p, i in zip(polys, layout["polygon_info"]):
        j = dict(i)
        j["centre"] = np.round(V[p].mean(0), 4).tolist()
        j.pop("cut", None)
        if any(inband[v] for v in p):
            j["spine"] = True
            dropped_pent += len(p) == 5 and not i.get("end")
        info.append(j)
    # strip outline in 3D (smile coordinates): both long edges of the spine
    strip = []
    for a in np.linspace(A_LO, A_HI, 160):
        N = np.array([-math.cos(a), 0, math.sin(a)]); B = np.array([0, -1.0, 0]); c = C + R * N
        row = []
        for sgn in (-1, 1):
            th = math.pi + sgn * (width / 2) / r
            row.append(np.round(smile(c + r * (math.cos(th) * N + math.sin(th) * B))[0], 3).tolist())
        strip.append(row)
    length = (R - r) * (A_HI - A_LO)
    bumps = [dict(node=int(v), sigma=round(float(st[v, 3]), 3), u=round(float(u[v]), 3)) for v in conn if -r <= st[v, 3] <= length + r]
    out = dict(layout)
    out["vertices"] = np.round(V, 4).tolist()
    out["polygon_info"] = info
    out["partition"] = layout.get("partition")
    out["description"] = "Smile tube with a spine. " + layout.get("description", "")
    out["spine"] = dict(width=width, bump_radius=bump_radius, hole=hole, length=round(length, 2),
                        band_nodes=[int(v) for v in np.where(inband)[0]], connections=[int(v) for v in conn],
                        bumps=bumps, strip=strip)
    out["params"] = dict(layout.get("params", {}), SPINE_WIDTH=width)
    return out, dict(nodes_in_band=int(inband.sum()), connections=len(conn), pentagons_lost=int(dropped_pent))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout"); ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=float, default=4.0, help="spine width in inches (default 4)")
    ap.add_argument("--bump-radius", type=float, default=1.0)
    a = ap.parse_args()
    res, rep = make(json.load(open(a.layout)), a.width, a.bump_radius)
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "layout.json"), "w"))
    print(rep, "spine length", res["spine"]["length"], "in")
    V = np.array(res["vertices"]); print("z range", V[:, 2].min().round(2), V[:, 2].max().round(2), "x range", V[:, 0].min().round(1), V[:, 0].max().round(1))


if __name__ == "__main__":
    main()
