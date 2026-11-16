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


def strip_polygon(width=4.0, length=None):
    """The spine strip in (sigma, u) inches: a `width` band with a gentle wave on both edges (the live edge)."""
    length = length if length is not None else (S.R - S.r) * (S.A_HI - S.A_LO)
    return S.organic_outline([], length, width)


def to_tube(sigma, u):
    """(sigma, u) -> a point on the tube, in the layout's own (original) coordinates."""
    a = S.A_LO + sigma / (S.R - S.r)
    th = math.pi + u / S.r
    N = np.array([-math.cos(a), 0, math.sin(a)]); B = np.array([0, -1.0, 0]); c = S.C + S.R * N
    return c + S.r * (math.cos(th) * N + math.sin(th) * B)


def clip(layout, width=4.0):
    V0 = np.array(layout["vertices"], float)
    st = np.array([S.station(p) for p in V0])
    su = st[:, [3, 2]]
    strip = strip_polygon(width)
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
            verts.append(tuple(to_tube(*pt)))
        return newkey[key]

    out_polys, out_info, band = [], [], set()
    for p, inf in zip(polys, info):
        ring = su[p]
        if np.abs(ring[:, 1]).min() > NEAR or np.ptp(ring[:, 1]) > 14:      # far from the spine, or wraps round the seam
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
