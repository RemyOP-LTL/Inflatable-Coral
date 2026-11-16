#!/usr/bin/env python3
"""
The spine piece (Remy, 2026-11-16). The spine follows a CURVE that comes with the surface file (see spinecurve.py), over the
whole length of the surface and the extra rows past its ends. Used by build_smile.py after clip_spine.py has cut the layout.
Needs shapely.
"""
import math

import numpy as np


def organic_outline(length, width=4.0, x0=0.0, wobble=0.25, wavelength=7.0):
    """The spine strip in (sigma, u) inches from sigma = x0 to x0 + length: a `width` band with a gentle wave on both edges."""
    from shapely.geometry import Polygon
    xs = np.linspace(x0, x0 + length, max(20, int(length * 4)))
    top = [(x, width / 2 + wobble * math.sin(2 * math.pi * x / wavelength)) for x in xs]
    bot = [(x, -width / 2 + wobble * math.sin(2 * math.pi * x / wavelength + 2.1)) for x in xs]
    return Polygon(top + bot[::-1]).buffer(0.6, 24).buffer(-0.6, 24).simplify(0.03)


def outline_mesh(poly):
    """Triangles filling the outline (so it can be drawn on the curved surface), as indices into a list of (sigma, u) points."""
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
        if poly.contains(t.centroid):
            tris.append([idx[(round(x, 4), round(y, 4))] for x, y in list(t.exterior.coords)[:3]])
    return pts, tris


def make(layout, curve, width=4.0, hole=0.25):
    """Describe the spine piece for a clipped, equalised layout: outline, nodes on its edge, spine spokes (tabs), 3D mesh."""
    from shapely.geometry import Polygon
    V = np.array(layout["vertices"], float)
    part = layout["partition"]
    sg, u, _ = curve.station(V)
    band = [int(v) for v in part["band"]]
    info = []
    for p, i in zip(layout["polygons"], layout["polygon_info"]):
        j = dict(i)
        j["centre"] = np.round(V[p].mean(0), 4).tolist()
        j.pop("cut", None)
        info.append(j)
    s0, s1 = 0.0, float(curve.length)
    poly = Polygon(layout["clip"]["outline"])
    pts2, tris = outline_mesh(poly)
    p2 = np.array(pts2)
    pts3 = np.round(curve.to3d(p2[:, 0], p2[:, 1]), 3).tolist()
    ss = np.linspace(s0, s1, 200)
    strip = [[np.round(a, 3).tolist(), np.round(b, 3).tolist()] for a, b in zip(curve.to3d(ss, np.full_like(ss, -width / 2)), curve.to3d(ss, np.full_like(ss, width / 2)))]
    attach = [dict(node=v, sigma=round(float(sg[v]), 3), u=round(float(u[v]), 3)) for v in band]
    bset = set(band)
    tabs = []
    for a, b in part.get("spine_spokes", []):
        e, w = (a, b) if a in bset else (b, a)
        d = np.array([sg[w] - sg[e], u[w] - u[e]]); n = float(np.linalg.norm(d)) or 1.0
        tabs.append(dict(edge=int(e), node=int(w), sigma=round(float(sg[e]), 3), u=round(float(u[e]), 3),
                         dir=[round(float(d[0] / n), 4), round(float(d[1] / n), 4)], L=round(float(np.linalg.norm(V[w] - V[e])), 3)))
    edges = []                                       # longer spokes that end on the spine: where, and which way they point (node -> spine edge)
    for a, b in part.get("edge_spokes", []):
        e, w = (a, b) if a in bset else (b, a)
        d = np.array([sg[e] - sg[w], u[e] - u[w]]); n = float(np.linalg.norm(d)) or 1.0
        edges.append(dict(edge=int(e), node=int(w), sigma=round(float(sg[e]), 3), u=round(float(u[e]), 3),
                          dir=[round(float(d[0] / n), 4), round(float(d[1] / n), 4)], d=round(float(np.linalg.norm(V[w] - V[e])), 3)))
    out = dict(layout)
    out["polygon_info"] = info
    out["description"] = "Cut by the spine. " + layout.get("description", "")
    out["spine"] = dict(width=width, hole=hole, length=round(s1 - s0, 2), s0=round(s0, 2), outline=[[round(x, 3), round(y, 3)] for x, y in poly.exterior.coords],
                        attach=attach, mesh=dict(pts=pts3, tris=tris), outline_length=round(s1 - s0, 2),
                        band_nodes=band, connections=band, tabs=tabs, edges=edges, bumps=attach, strip=strip)
    out["params"] = dict(layout.get("params", {}), SPINE_WIDTH=width)
    return out, dict(band_nodes=len(band), spine_spokes=len(tabs), edge_spokes=len(edges), partial_cells=sum(bool(i.get("partial")) for i in info),
                     pentagons_lost=sum(bool(i.get("partial")) and i.get("was_sides") == 5 for i in info))
