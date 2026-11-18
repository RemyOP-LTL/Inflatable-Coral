#!/usr/bin/env python3
"""
The spine comes first (Remy, 2026-11-16): the pattern is cut by the spine, so no spoke lies on or crosses it.

Takes a layout on the bent tube (original, not yet stood up) and the spine strip, and
  - removes every node inside the strip,
  - cuts every spoke that runs into the strip at the strip's edge, which makes a new node there (a "band" node),
  - cuts every cell the strip touches into a partial window (it need not be a pentagon or hexagon any more).
A spoke from outside to a band node is a spine spoke: a tab of the spine piece, ending at the edge of the strip.

TUBE-SPECIFIC like spine.py (the strip is laid along the inside line of the bent tube).
Needs shapely.
"""
import math

import numpy as np
from shapely.geometry import Point, Polygon

import spine as S

NEAR = 9.0           # only cells with a corner this close (inches, across) to the spine line are looked at


def strip_polygon(curve, width=4.0):
    """The spine strip in (sigma, u) inches: exactly the length of the curve (the surface), flush with both ends."""
    return S.organic_outline(float(curve.length), width, x0=0.0)


def _clip(layout, strip, width, curve):
    V0 = np.array(layout["vertices"], float)
    sg0, u0, dist0 = curve.station(V0)
    su = np.stack([sg0, u0], 1)
    boundary = strip.exterior
    inside = np.array([strip.contains(Point(*p)) for p in su])
    polys, info = layout["polygons"], layout["polygon_info"]
    verts = [tuple(p) for p in V0]                       # grows with new nodes
    newkey = {}                                          # rounded (sigma,u) -> node id

    def node_at(pt):
        for i in np.where(np.hypot(su[:, 0] - pt[0], su[:, 1] - pt[1]) < 1e-6)[0]:
            return int(i)
        key = (round(pt[0], 3), round(pt[1], 3))
        if key not in newkey:
            newkey[key] = len(verts)
            verts.append(tuple(curve.to3d(pt[0], pt[1])[0]))
        return newkey[key]

    out_polys, out_info, band = [], [], set()
    for p, inf in zip(polys, info):
        ring = su[p]
        if dist0[p].min() > NEAR:                                           # far from the spine
            out_polys.append(list(p)); out_info.append(dict(inf)); continue
        P = Polygon(ring)
        if not P.is_valid:
            P = P.buffer(0)
        if not P.intersects(strip) or P.intersection(strip).area < 1e-6 and not inside[p].any():
            out_polys.append(list(p)); out_info.append(dict(inf)); continue
        # where the cell's outline crosses the strip's edge
        X = P.exterior.intersection(boundary)
        cross = [(g.x, g.y) for g in getattr(X, "geoms", [X]) if g.geom_type == "Point"]
        keep = {tuple(np.round(su[v], 6)): v for v in p}
        orig_area_sign = 1.0 if Polygon(ring).exterior.is_ccw else -1.0
        for piece in getattr(P.difference(strip), "geoms", [P.difference(strip)]):
            if piece.geom_type != "Polygon" or piece.area < 0.3:
                continue
            ids = []
            for x, y in list(piece.exterior.coords)[:-1]:
                k = tuple(np.round((x, y), 6))
                if k in keep:
                    ids.append(keep[k]); continue
                if any(math.hypot(x - cx, y - cy) < 1e-4 for cx, cy in cross):
                    v = node_at((x, y)); band.add(v); ids.append(v)
            ids = [v for i, v in enumerate(ids) if v != ids[i - 1]]
            if len(ids) < 3:
                continue
            if (1.0 if piece.exterior.is_ccw else -1.0) != orig_area_sign:
                ids = ids[::-1]
            j = dict(inf); j["spine"] = True; j["partial"] = True; j["was_sides"] = len(p)
            out_polys.append(ids); out_info.append(j)
    # drop nodes nothing uses, renumber
    used = sorted({v for p in out_polys for v in p})
    remap = {v: i for i, v in enumerate(used)}
    Vn = np.array(verts)[used]
    res = dict(layout)
    res["vertices"] = np.round(Vn, 4).tolist()
    res["polygons"] = [[remap[v] for v in p] for p in out_polys]
    res["polygon_info"] = out_info
    res["clip"] = dict(width=width, band=sorted(remap[v] for v in band), nodes_removed=int(len(V0) - len([v for v in used if v < len(V0)])))
    return res, strip


def stubs(res, curve):
    """Spine spokes of a clipped layout: (edge node, far node, edge point (sigma,u), far point, length in the surface)."""
    V = np.array(res["vertices"], float)
    band = set(res["clip"]["band"])
    sg, uu, _ = curve.station(V)
    su = {v: (float(sg[v]), float(uu[v])) for v in range(len(V))}
    out, seen = [], set()
    for p in res["polygons"]:
        for a, b in zip(p, p[1:] + p[:1]):
            if (a in band) != (b in band) and frozenset((a, b)) not in seen:
                seen.add(frozenset((a, b)))
                e, n = (a, b) if a in band else (b, a)
                out.append((e, n, su[e], su[n], float(np.linalg.norm(V[e] - V[n]))))
    return out


TAB_MAX = 1.5        # a spine spoke up to this long (inches, edge of the spine to its node) stays a tab of the spine


def clip(layout, curve, width=4.0, tab_max=TAB_MAX):
    """Cut the layout by the spine strip. Spokes from the spine's edge to a node that are short stay as tabs of the spine piece;
    longer ones would form peninsulas, so they become ordinary spokes ('edge spokes') from their node to the spine's edge, with their
    tip overlapping the spine, as spokes coming off the neighbouring patches."""
    strip = strip_polygon(curve, width)
    res, _ = _clip(layout, strip, width, curve)
    st = stubs(res, curve)
    res["clip"]["outline"] = [[round(x, 3), round(y, 3)] for x, y in strip.exterior.coords]
    res["clip"]["edge"] = [[int(e), int(n)] for e, n, E, N, d in st if d > tab_max]
    res["clip"]["tab_max"] = tab_max
    res["clip"]["long_stubs"] = 0
    res["clip"]["stub_max"] = round(max([d for *_, d in st if d <= tab_max] or [0.0]), 2)
    return res, strip
