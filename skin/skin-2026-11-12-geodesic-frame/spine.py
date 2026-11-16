#!/usr/bin/env python3
"""
The smile tube with a spine (Remy, 2026-11-15).

1. Stands the bent test tube up so its bend is a smile seen from the front: the middle of the tube
   touches the ground plane (z = 0, Fusion's "Top" plane) and both ends curve up.
2. Lays a solid SPINE, 4 in wide, along the top line on the inside of the curve.
3. Nodes that fall inside the spine are dropped; every spoke that ran into the spine now ends on it, at a
   rivet hole with a round bump on the spine edge. Pentagon plates that touch the spine are dropped.

TUBE-SPECIFIC (like hex57's TestTube): it knows the tube is a circular arc (BEND_RADIUS) of radius TUBE_RADIUS.

Used by build_smile.py (clip_spine.py cuts the layout by the strip first).
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



def to_3d(sigma, u):
    """Flat spine coordinates (distance along, distance across) -> a point on the tube, in smile coordinates."""
    a = A_LO + sigma / (R - r)
    th = math.pi + u / r
    N = np.array([-math.cos(a), 0, math.sin(a)]); B = np.array([0, -1.0, 0]); c = C + R * N
    return smile(c + r * (math.cos(th) * N + math.sin(th) * B))[0]


def organic_outline(attach, length, width=4.0, reach=1.5, fillet=1.6, wobble=0.25, wavelength=7.0):
    """A live edge: the spine is a `width` strip whose long edges swell out to every attachment point and ease back
    in between, with a slight wave of their own. Returns the outline as a shapely polygon in (sigma, u) inches.
    attach = [(sigma, u)]; every attachment end is kept `reach` inside the outline (spoke end radius + rim)."""
    from shapely.geometry import Polygon, Point, box
    from shapely.ops import unary_union
    xs = np.linspace(-0.5, length + 0.5, 400)
    top = [(x, width / 2 + wobble * math.sin(2 * math.pi * x / wavelength)) for x in xs]
    bot = [(x, -width / 2 + wobble * math.sin(2 * math.pi * x / wavelength + 2.1)) for x in xs]
    base = Polygon(top + bot[::-1])
    blobs = [Point(s_, u_).buffer(reach, 32) for s_, u_ in attach]
    shape = unary_union([base] + blobs)
    shape = shape.buffer(fillet, 24).buffer(-fillet, 24)                 # closing: fillets where a swelling meets the strip
    shape = shape.buffer(-0.6, 24).buffer(0.6, 24)                       # opening: no sharp tips
    if shape.geom_type != "Polygon":
        shape = max(shape.geoms, key=lambda g: g.area)
    return shape.simplify(0.03)


def outline_mesh(poly):
    """Triangles filling the outline (so it can be drawn on the curved tube), as indices into a list of 3D points."""
    from shapely.geometry import MultiPoint, Point
    from shapely.ops import triangulate
    pts = []
    ring = list(poly.exterior.coords)[:-1]
    for a, b in zip(ring, ring[1:] + ring[:1]):                           # boundary, at least every inch
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1])))
        pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    minx, miny, maxx, maxy = poly.bounds
    for x in np.arange(minx, maxx, 1.5):
        for y in np.arange(miny, maxy, 1.0):
            p = Point(x, y)
            if poly.contains(p) and poly.exterior.distance(p) > 0.4:
                pts.append((x, y))
    pts = list(dict.fromkeys((round(x, 4), round(y, 4)) for x, y in pts))
    idx = {p: i for i, p in enumerate(pts)}
    tris = []
    for t in triangulate(MultiPoint(pts)):
        c = t.centroid
        if poly.contains(c):
            tris.append([idx[(round(x, 4), round(y, 4))] for x, y in list(t.exterior.coords)[:3]])
    return pts, tris


def make(layout, width=4.0, hole=0.25):
    """Stand the clipped, equalised layout up as the smile and describe the spine piece: its outline, the nodes on
    its edge, and the spine spokes (tabs that leave the edge toward a node)."""
    V0 = np.array(layout["vertices"], float)
    st = np.array([station(p) for p in V0])
    part = layout["partition"]
    band = [int(v) for v in part["band"]]
    V = smile(V0)
    info = []
    for p, i in zip(layout["polygons"], layout["polygon_info"]):
        j = dict(i)
        j["centre"] = np.round(V[p].mean(0), 4).tolist()
        j.pop("cut", None)
        info.append(j)
    strip = []                                                            # both long edges of the spine in 3D (smile coordinates)
    for a in np.linspace(A_LO, A_HI, 160):
        N = np.array([-math.cos(a), 0, math.sin(a)]); B = np.array([0, -1.0, 0]); c = C + R * N
        row = []
        for sgn in (-1, 1):
            th = math.pi + sgn * (width / 2) / r
            row.append(np.round(smile(c + r * (math.cos(th) * N + math.sin(th) * B))[0], 3).tolist())
        strip.append(row)
    length = (R - r) * (A_HI - A_LO)
    poly = organic_outline([], length, width)
    pts2, tris = outline_mesh(poly)
    pts3 = [np.round(to_3d(x, y), 3).tolist() for x, y in pts2]
    attach = [dict(node=v, sigma=round(float(st[v, 3]), 3), u=round(float(st[v, 2]), 3)) for v in band]
    bset = set(band)
    tabs = []                                                             # spine spokes, drawn flat as tabs off the spine's edge
    for a, b in part.get("spine_spokes", []):
        e, w = (a, b) if a in bset else (b, a)
        d = np.array([st[w, 3] - st[e, 3], st[w, 2] - st[e, 2]]); n = float(np.linalg.norm(d)) or 1.0
        tabs.append(dict(edge=int(e), node=int(w), sigma=round(float(st[e, 3]), 3), u=round(float(st[e, 2]), 3),
                         dir=[round(float(d[0] / n), 4), round(float(d[1] / n), 4)], L=round(float(np.linalg.norm(V0[w] - V0[e])), 3)))
    out = dict(layout)
    out["vertices"] = np.round(V, 4).tolist()
    out["polygon_info"] = info
    out["description"] = "Smile tube, cut by the spine. " + layout.get("description", "")
    out["spine"] = dict(width=width, hole=hole, length=round(length, 2), outline=[[round(x, 3), round(y, 3)] for x, y in poly.exterior.coords],
                        attach=attach, mesh=dict(pts=pts3, tris=tris), outline_length=round(length, 2),
                        band_nodes=band, connections=band, tabs=tabs, bumps=attach, strip=strip)
    out["params"] = dict(layout.get("params", {}), SPINE_WIDTH=width)
    return out, dict(band_nodes=len(band), spine_spokes=len(tabs), partial_cells=sum(bool(i.get("partial")) for i in info),
                     pentagons_lost=sum(bool(i.get("partial")) and i.get("was_sides") == 5 for i in info))


if __name__ == "__main__":
    sys.exit("Use build_smile.py: it clips the layout by the spine, equalises, then calls spine.make.")
