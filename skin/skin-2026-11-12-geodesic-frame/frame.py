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

    def pentagons(self, rings=1):
        """Pentagons whose whole patch lies on the real skin (not on the greyed extension)."""
        out = []
        for p, s in enumerate(self.sides):
            if s == 5 and not self.end[p]:
                ok = all(not self.end[q] for q in self.ring_polys(p, rings + 1))
                out.append(dict(id=p, ok=ok, centre=self.info[p]["centre"]))
        return out

    # ---- the flattening --------------------------------------------------------------------
    def flatten(self, pent, rings=1):
        """Lay one pentagon patch flat. Returns plain data (flat positions in inches, spokes, cuts)."""
        V = self.V
        pp = self.ring_polys(pent, rings)
        S_edges = {e for e, ps in self.edge_polys.items() if any(q in pp for q in ps)}
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
        joint = {v for v in pos if any(frozenset((v, w)) not in S_edges for w in self.adj[v])}
        plate_err = max(abs(float(np.linalg.norm(pos[a] - pos[b])) - float(np.linalg.norm(V[a] - V[b])))
                        for a, b in map(tuple, plate_edges))
        return dict(pent=pent, rings=rings, pos=pos, solid=solid, cuts=cuts, joint=joint, plate=plate,
                    plate_err=plate_err, windows=sorted(q for q in pp if q != pent),
                    pent_in_patch=[q for q in pp if q != pent and self.sides[q] == 5])


# ---- sizes and the sheet --------------------------------------------------------------------
def bounds(points, pad=0.0):
    P = np.array(points)
    return P.min(0) - pad, P.max(0) + pad


def best_fit_on_sheet(points, pad=0.75):
    """Smallest bounding rectangle over rotations, and whether it fits a 48 x 96 in sheet."""
    P = np.array(points)
    best = None
    for deg in np.arange(0, 90, 1.0):
        t = math.radians(deg)
        R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
        Q = P @ R.T
        w, h = (Q.max(0) - Q.min(0)) + 2 * pad
        if best is None or w * h < best[0]:
            best = (w * h, deg, w, h)
    _, deg, w, h = best
    return dict(angle=float(deg), w=float(w), h=float(h), fits=bool(min(w, h) <= SHEET[0] and max(w, h) <= SHEET[1]))


def patch_stats(fr, patch, opts):
    pts = list(patch["pos"].values()) + [c["free"] for c in patch["cuts"]]
    gaps = sorted((c["gap"] for c in patch["cuts"]), reverse=True)
    return dict(
        pentagon=patch["pent"], rings=patch["rings"], windows=len(patch["windows"]),
        hubs=len(patch["pos"]), spokes=len(patch["solid"]) + len(patch["cuts"]),
        cuts=len(gaps), gap_max=gaps[0] if gaps else 0.0, gap_mean=float(np.mean(gaps)) if gaps else 0.0,
        gaps=[round(g, 3) for g in gaps], plate_err=patch["plate_err"], pent_in_patch=patch["pent_in_patch"],
        joints=len(patch["joint"]), size=best_fit_on_sheet(pts, opts["circle_diameter"] / 2))


# ---- drawing (SVG, 1 unit = 1 inch, so it can go straight into Fusion or a CAM program) -----------
def patch_svg(fr, patch, opts, show_labels=True, title=None):
    o = {**DEFAULTS, **opts}
    sw, cd, rh = o["spoke_width"], o["circle_diameter"], o["rivet_hole"]
    pos = patch["pos"]
    pts = list(pos.values()) + [c["free"] for c in patch["cuts"]]
    c0 = np.mean([pos[v] for v in patch["plate"]], axis=0)
    hub_r = max(float(np.linalg.norm(pos[v] - c0)) for v in patch["plate"]) + cd / 2
    pad = cd / 2 + 1.2
    lo, hi = bounds(pts, pad)
    if o["plate"] == "round":
        lo, hi = np.minimum(lo, c0 - hub_r - 0.5), np.maximum(hi, c0 + hub_r + 0.5)
    W, H = hi - lo
    X = lambda p: f"{p[0] - lo[0]:.3f}"
    Y = lambda p: f"{hi[1] - p[1]:.3f}"                        # SVG y points down
    ink, fill, free_c, plate_c = "#1c3d2e", "#3aa675", "#e0752b", "#f2a65a"
    under, over = [], []

    def bar(a, b, color, wid):
        return f'<line x1="{X(a)}" y1="{Y(a)}" x2="{X(b)}" y2="{Y(b)}" stroke="{color}" stroke-width="{wid:.3f}"/>'

    def disc(p, r, color):
        return f'<circle cx="{X(p)}" cy="{Y(p)}" r="{r:.3f}" fill="{color}" stroke="{color}"/>'

    items = []                                                   # (a, b, colour) bars and (p, r, colour) discs
    plate_pts = [pos[v] for v in patch["plate"]]
    for a, b in patch["solid"]:
        items.append(("bar", pos[a], pos[b], fill))
    for c in patch["cuts"]:
        items.append(("bar", pos[c["own"]], c["free"], free_c))
    hubs = set(pos) - (set(patch["plate"]) if o["plate"] == "round" else set())
    for v in hubs:
        items.append(("disc", pos[v], cd / 2, fill))
    for c in patch["cuts"]:
        items.append(("disc", c["free"], cd / 2, free_c))
    # dark underlay (grows every shape by 0.04 in) then the colours: shows one clean outline round the union
    g = 0.04
    for it in items:
        if it[0] == "bar":
            under.append(bar(it[1], it[2], ink, sw + 2 * g))
        else:
            under.append(disc(it[1], it[2] + g, ink))
    if o["plate"] == "round":
        under.append(disc(c0, hub_r + g, ink))
        over.append(disc(c0, hub_r, plate_c))
    else:
        pstr = " ".join(f"{X(p)},{Y(p)}" for p in plate_pts)
        under.append(f'<polygon points="{pstr}" fill="{ink}" stroke="{ink}" stroke-width="{2 * g}" stroke-linejoin="round"/>')
        over.append(f'<polygon points="{pstr}" fill="{plate_c}" stroke="{plate_c}" stroke-linejoin="round"/>')
    for it in items:
        if it[0] == "bar":
            over.append(bar(it[1], it[2], it[3], sw))
        else:
            over.append(disc(it[1], it[2], it[3]))
    over.append(f'<circle cx="{X(c0)}" cy="{Y(c0)}" r="{fr.hole_diameter / 2:.3f}" fill="#fff" stroke="{ink}" stroke-width="0.06"/>')
    # rivet holes: both ends of every cut spoke, and hubs that join the next patch
    holes = [c["free"] for c in patch["cuts"]] + [pos[c["target"]] for c in patch["cuts"]]
    holes_j = [pos[v] for v in patch["joint"] if v not in {c["target"] for c in patch["cuts"]}]
    for p in holes:
        over.append(f'<circle cx="{X(p)}" cy="{Y(p)}" r="{rh / 2:.3f}" fill="#fff" stroke="{ink}" stroke-width="0.04"/>')
    for p in holes_j:
        over.append(f'<circle cx="{X(p)}" cy="{Y(p)}" r="{rh / 2:.3f}" fill="#fff" stroke="#3b6fb0" stroke-width="0.05"/>')
    pull = []
    for c in patch["cuts"]:
        a, b = c["free"], pos[c["target"]]
        pull.append(f'<line x1="{X(a)}" y1="{Y(a)}" x2="{X(b)}" y2="{Y(b)}" stroke="#c0281d" stroke-width="0.09" stroke-dasharray="0.35 0.25"/>')
        if show_labels:
            m = (a + b) / 2
            pull.append(f'<text x="{X(m)}" y="{Y(m + np.array([0, 0.45]))}" font-size="0.95" text-anchor="middle" fill="#c0281d" '
                        f'stroke="#fff" stroke-width="0.22" paint-order="stroke" font-family="sans-serif">{c["gap"]:.2f}</text>')
    sb = lo + np.array([1.0, 1.0])
    scale = (f'<line x1="{X(sb)}" y1="{Y(sb)}" x2="{X(sb + np.array([6, 0]))}" y2="{Y(sb)}" stroke="#222" stroke-width="0.15"/>'
             f'<text x="{X(sb + np.array([0, 0.35]))}" y="{Y(sb + np.array([0, 0.35]))}" font-size="1.0" font-family="sans-serif" fill="#222">6 in</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}" width="{W:.2f}in" height="{H:.2f}in" '
            f'font-family="sans-serif">' + "".join(under) + "".join(over) + "".join(pull) + scale + "</svg>")
