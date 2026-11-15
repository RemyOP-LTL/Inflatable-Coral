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
        """Pentagons whose whole patch lies on the real skin (not on the greyed extension) and not on the spine."""
        out = []
        for p, s in enumerate(self.sides):
            if s == 5 and not self.end[p]:
                ok = all(not self.end[q] for q in self.ring_polys(p, rings + 1)) and not self.on_spine[p]
                out.append(dict(id=p, ok=ok, centre=self.info[p]["centre"], spine=self.on_spine[p]))
        return out

    # ---- the flattening --------------------------------------------------------------------
    def flatten(self, pent, rings=1):
        """Lay one pentagon patch flat. Returns plain data (flat positions in inches, spokes, cuts)."""
        V = self.V
        pp = self.ring_polys(pent, rings)
        S_edges = {e for e, ps in self.edge_polys.items() if any(q in pp for q in ps) and not self.hidden(e)}
        plate = self.polys[pent]
        P3 = V[plate]; o = P3.mean(0); n = newell(P3)
        e1 = P3[0] - o; e1 = e1 - n * np.dot(e1, n); e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        # the plate is rigid: its corners projected into its own best-fit plane
        pos = {v: np.array([np.dot(V[v] - o, e1), np.dot(V[v] - o, e2)]) for v in plate}
        plate_edges = {frozenset(e) for e in zip(plate, plate[1:] + plate[:1])}
        order = {v: i for i, v in enumerate(plate)}
        depth = {v: 0 for v in plate}
        parent = {}
        tree = set(plate_edges)
        dirs = {}

        def ang(a, b):
            d = pos[b] - pos[a]
            return math.atan2(d[1], d[0])

        def predict(x, known, target):
            """Flat direction of spoke x->target, from the flat direction of spoke x->known and the 3D angle between them."""
            nb = self.ccw(x)
            sign = 1.0 if (nb.index(target) - nb.index(known)) % len(nb) == 1 else -1.0
            return ang(x, known) + sign * self.angle3d(x, known, target)

        queue = deque(plate)
        while queue:                                   # breadth first, outward from the plate
            x = queue.popleft()
            nb = self.ccw(x)
            d = {}
            if x in plate:
                ks = [w for w in nb if w in plate]
                for w in ks:
                    d[w] = ang(x, w)
                for w in nb:
                    if w not in d:                     # spoke leaving the plate: average of two predictions
                        a = [predict(x, k, w) for k in ks]
                        d[w] = math.atan2(sum(math.sin(t) for t in a), sum(math.cos(t) for t in a))
            else:
                pr = parent[x]
                d[pr] = ang(x, pr)
                for w in nb:
                    if w != pr:
                        d[w] = predict(x, pr, w)
            dirs[x] = d
            for w in nb:
                e = frozenset((x, w))
                if e not in S_edges or e in plate_edges or w in pos:
                    continue
                L = float(np.linalg.norm(V[w] - V[x]))
                pos[w] = pos[x] + L * np.array([math.cos(d[w]), math.sin(d[w])])
                parent[w] = x; depth[w] = depth[x] + 1; order[w] = len(order)
                tree.add(e); queue.append(w)
        # spokes that are not in the tree: the owner (nearer the plate) keeps the spoke, its far end is free
        cuts, solid = [], []
        for e in S_edges:
            if e in plate_edges:
                continue
            a, b = tuple(e)
            if e in tree:
                solid.append((a, b)); continue
            own, tgt = (a, b) if (depth[a], order[a]) <= (depth[b], order[b]) else (b, a)
            L = float(np.linalg.norm(V[a] - V[b]))
            th = dirs[own][tgt]
            free = pos[own] + L * np.array([math.cos(th), math.sin(th)])
            cuts.append(dict(own=own, target=tgt, free=free, gap=float(np.linalg.norm(free - pos[tgt])), length=L))
        # hubs that also join a spoke outside this patch (the next patch will meet them there)
        joint = {v for v in pos if any(frozenset((v, w)) not in S_edges and not self.hidden(frozenset((v, w))) for w in self.adj[v])}
        plate_err = max(abs(float(np.linalg.norm(pos[a] - pos[b])) - float(np.linalg.norm(V[a] - V[b])))
                        for a, b in map(tuple, plate_edges))
        return dict(pent=pent, rings=rings, pos=pos, solid=solid, cuts=cuts, joint=joint, plate=plate,
                    plate_err=plate_err, windows=sorted(q for q in pp if q != pent), on_spine=sorted(v for v in pos if v in self.band),
                    pent_in_patch=[q for q in pp if q != pent and self.sides[q] == 5])


# ---- what the page needs ------------------------------------------------------------------------
def patch_data(fr, patch):
    """Plain data for one flattened patch (inches). The page (patch_draw.js) does the rest: spreading the free ends
    apart so the parts can be cut, drawing, sizes. Flat positions are keyed by hub number."""
    pos = patch["pos"]
    r2 = lambda p: [round(float(p[0]), 4), round(float(p[1]), 4)]
    return dict(
        pent=patch["pent"], rings=patch["rings"], hole=fr.hole_diameter,
        plate=patch["plate"], pos={str(v): r2(p) for v, p in pos.items()},
        solid=[[a, b] for a, b in patch["solid"]],
        cuts=[dict(own=c["own"], target=c["target"], L=round(c["length"], 4), free0=r2(c["free"])) for c in patch["cuts"]],
        joint=sorted(patch["joint"]), windows=sorted(patch["windows"]), pent_in_patch=patch["pent_in_patch"],
        window_nodes=[[v for v in fr.polys[q] if v in pos] for q in sorted(patch["windows"])],
        on_spine=[int(v) for v in patch["on_spine"]],
        plate_err=round(patch["plate_err"], 4))
