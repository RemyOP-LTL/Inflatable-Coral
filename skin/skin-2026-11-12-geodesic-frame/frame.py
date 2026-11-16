#!/usr/bin/env python3
"""
Geodesic-frame idea (Remy, 2026-11-12): the skin as a FRAME.

  hub    = a corner of today's polygons (3 spokes meet there)
  spoke  = an edge of today's polygons, a strip of plastic SPOKE_WIDTH wide, hub to hub
  hub circle = a CIRCLE_DIAMETER circle of plastic at every hub, where spokes meet
  pentagon   = not a window: a solid plate (the polyp hole goes in it)
  hexagons / heptagons = open windows in the frame

A PATCH is one pentagon plate plus the rings of windows around it. Laid flat, the windows do not
quite close (the surface is curved, and the pentagon/heptagon pairs are lattice defects), so some
spokes come up short: they end at a free circle that sits GAP inches away from the hub it belongs to.
You pull that circle to the hub and rivet through the small hole in both.

This file is the maths. frame_app.py is the web page around it.
Everything is in inches. Needs numpy only.
"""
import json
import math
from collections import deque

import numpy as np

from partition import partition as make_partition

DEFAULTS = dict(rings=1, spoke_width=1.0, circle_diameter=1.5, rivet_hole=0.25, plate="outline")
SHEET = (48.0, 96.0)          # 4 x 8 ft sheet, inches


def newell(P):
    """Unit normal of a polygon (corner list), pointing outward because layouts list corners anticlockwise from outside."""
    n = np.zeros(3)
    for a, b in zip(P, np.roll(P, -1, axis=0)):
        n += np.cross(a, b)
    return n / (np.linalg.norm(n) or 1.0)


class Frame:
    def __init__(self, layout):
        if isinstance(layout, str):
            layout = json.load(open(layout))
        self.layout = layout
        self.V = np.array(layout["vertices"], float)
        self.polys = [list(p) for p in layout["polygons"]]
        self.info = layout["polygon_info"]
        self.params = layout.get("params", {})
        self.end = [bool(i.get("end")) for i in self.info]
        self.sides = [len(p) for p in self.polys]
        self.pnorm = [newell(self.V[p]) for p in self.polys]
        self.edge_polys = {}
        for pi, poly in enumerate(self.polys):
            for a, b in zip(poly, poly[1:] + poly[:1]):
                self.edge_polys.setdefault(frozenset((a, b)), []).append(pi)
        self.adj = {}
        for e in self.edge_polys:
            a, b = tuple(e)
            self.adj.setdefault(a, set()).add(b)
            self.adj.setdefault(b, set()).add(a)
        self.vpolys = {}
        for pi, poly in enumerate(self.polys):
            for v in poly:
                self.vpolys.setdefault(v, []).append(pi)
        self.vnorm = {}
        for v, ps in self.vpolys.items():
            n = sum(self.pnorm[p] for p in ps)
            self.vnorm[v] = n / (np.linalg.norm(n) or 1.0)
        self.hole_diameter = float(self.params.get("HOLE_DIAMETER") or 5.0)
        self.spine = layout.get("spine")
        self.band = set(self.spine["band_nodes"]) if self.spine else set()
        self.on_spine = [bool(i.get("spine")) for i in self.info]
        part = layout.get("partition") or make_partition(layout, self.band)
        self.part = part
        self.tree = {frozenset(e) for e in part["tree"]}
        self.arms = {int(k): [tuple(a) for a in v] for k, v in part.get("arms", {}).items()}
        self.loose = [tuple(e) for e in part["loose"]]
        self.loose_id = {frozenset(e): i + 1 for i, e in enumerate(self.loose)}
        self.spine_spokes = {frozenset(e) for e in part.get("spine_spokes", [])}
        self._ccw = {}

    # ---- helpers -------------------------------------------------------------------------
    def ccw(self, v):
        """Neighbours of hub v in anticlockwise order, seen from outside the surface."""
        if v not in self._ccw:
            n = self.vnorm[v]
            ref = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
            e1 = np.cross(n, ref); e1 /= np.linalg.norm(e1)
            e2 = np.cross(n, e1)
            key = lambda w: math.atan2(np.dot(self.V[w] - self.V[v], e2), np.dot(self.V[w] - self.V[v], e1))
            self._ccw[v] = sorted(self.adj[v], key=key)
        return self._ccw[v]

    def angle3d(self, v, a, b):
        """Angle at hub v between spokes to a and b, measured in 3D."""
        u, w = self.V[a] - self.V[v], self.V[b] - self.V[v]
        c = np.dot(u, w) / (np.linalg.norm(u) * np.linalg.norm(w))
        return math.acos(max(-1.0, min(1.0, c)))

    def poly_neighbours(self, p):
        out = set()
        for a, b in zip(self.polys[p], self.polys[p][1:] + self.polys[p][:1]):
            out.update(self.edge_polys[frozenset((a, b))])
        out.discard(p)
        return out

    def ring_polys(self, p, rings):
        seen, frontier = {p}, [p]
        for _ in range(rings):
            nxt = []
            for q in frontier:
                for r in self.poly_neighbours(q):
                    if r not in seen:
                        seen.add(r); nxt.append(r)
            frontier = nxt
        return seen

    def hidden(self, e):
        """A spoke with both ends inside the spine is not there: the spine is."""
        a, b = tuple(e)
        return a in self.band and b in self.band

    def pentagons(self, rings=1):
        """Plates, and whether their part (the plate and its attached spokes) lies on the real skin, not on the greyed
        extension at the ends. A plate that touches the spine is lost (no polyp there)."""
        out = []
        for p, s_ in enumerate(self.sides):
            if self.on_spine[p]:
                if self.info[p].get("was_sides") == 5 and not self.end[p]:       # a pentagon the spine cut: no polyp there
                    out.append(dict(id=p, ok=False, centre=self.info[p]["centre"], spine=True))
                continue
            if s_ == 5 and not self.end[p]:
                nodes = set(self.polys[p]) | {w for _, w in self.arms.get(p, [])}
                ok = all(not self.end[q] for v in nodes for q in self.vpolys[v])
                out.append(dict(id=p, ok=ok, centre=self.info[p]["centre"], spine=False))
        return out

    # ---- the flattening --------------------------------------------------------------------
    def flatten(self, pent, rings=1):
        """Lay one part flat: the pentagon plate and its arms (the spokes at its five corners).
        The plate is rigid and flat. Each arm is hinged at its corner: in the flat it keeps the direction it has when seen
        from straight above the plate (so its angle to the plate's sides is as in 3D), and its full length. When the part
        is built the arm folds up out of the flat sheet by `tilt` degrees along a straight fold line, so its far end
        lands where it belongs on the curved skin."""
        V = self.V
        plate = self.polys[pent]
        P3 = V[plate]; o = P3.mean(0); n = newell(P3)
        e1 = P3[0] - o; e1 = e1 - n * np.dot(e1, n); e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        pos = {v: np.array([np.dot(V[v] - o, e1), np.dot(V[v] - o, e2)]) for v in plate}
        plate_edges = {frozenset(e) for e in zip(plate, plate[1:] + plate[:1])}
        solid, arms = [], []
        for v, w in self.arms.get(pent, []):
            d3 = V[w] - V[v]
            h = float(np.dot(d3, n))                                     # how far the far end sits above the plate's plane
            q = np.array([np.dot(d3, e1), np.dot(d3, e2)])
            if np.linalg.norm(q) < 1e-6:                                 # straight up: point it away from the plate centre
                q = pos[v]
            az = math.atan2(q[1], q[0])
            L = float(np.linalg.norm(d3))
            pos[w] = pos[v] + L * np.array([math.cos(az), math.sin(az)])
            solid.append((v, w))
            arms.append(dict(corner=v, far=w, tilt=math.degrees(math.atan2(h, float(np.linalg.norm(q)))), length=L))
        nodes = set(pos)
        ends = []                                                        # loose and spine spokes that rivet to a node of this part
        for (a_, b_) in self.loose:
            key = frozenset((a_, b_))
            for v in (a_, b_):
                if v in nodes and v not in plate:
                    ends.append(dict(id=self.loose_id[key], node=v, spine=False))
        for key in self.spine_spokes:
            for v in key:
                if v in nodes and v not in self.band:
                    ends.append(dict(id=0, node=v, spine=True))
        plate_err = max(abs(float(np.linalg.norm(pos[a] - pos[b])) - float(np.linalg.norm(V[a] - V[b])))
                        for a, b in map(tuple, plate_edges))
        return dict(pent=pent, rings=rings, pos=pos, solid=solid, arms=arms, cuts=[], ends=ends, joint=set(), plate=plate,
                    plate_err=plate_err, windows=[], on_spine=[], pent_in_patch=[])


# ---- what the page needs ------------------------------------------------------------------------
def patch_data(fr, patch):
    """Plain data for one flattened part (inches). The page (patch_draw.js) nests the loose spokes in the flat and draws it."""
    pos = patch["pos"]
    r2 = lambda p: [round(float(p[0]), 4), round(float(p[1]), 4)]
    return dict(
        pent=patch["pent"], hole=fr.hole_diameter, plate=patch["plate"], pos={str(v): r2(p) for v, p in pos.items()},
        solid=[[a, b] for a, b in patch["solid"]],
        cuts=[dict(id=c["id"], own=c["own"], target=c["target"], L=round(c["length"], 4)) for c in patch["cuts"]],
        ends=[dict(id=e["id"], node=e["node"], spine=e["spine"]) for e in patch["ends"]],
        joint=[], windows=sorted(patch["windows"]), pent_in_patch=[],
        window_nodes=[], on_spine=[], plate_err=round(patch["plate_err"], 4),
        arms=[dict(corner=a["corner"], far=a["far"], tilt=round(a["tilt"], 2), L=round(a["length"], 4)) for a in patch["arms"]])
