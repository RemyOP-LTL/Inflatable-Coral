#!/usr/bin/env python3
"""
Patches: parts (a pentagon plate and its arms) joined into one flat piece, as big as will fit a 4 x 8 ft sheet.

Two parts are INTERCONNECTED when they share a node: an arm of one ends on a corner of the other, or the arms of both
end on the same node. A patch is a tree of parts grown from a first pentagon. Each new part is placed by the same hinge
rule as an arm: the spoke that joins it keeps the angle it has in 3D (seen from above the plate it hinges on), so
nothing is stretched; the curved skin is made by folding along the fold lines. A part is added only if it does not
overlap what is already placed and the patch still fits a 48 x 96 in sheet. Needs numpy and shapely.
"""
import math

import numpy as np
from shapely import affinity
from shapely.geometry import Point
from shapely.ops import unary_union

import geom
from frame import newell

SHEET = (48.0, 96.0)
OVERLAP_OK = 0.15            # square inches of overlap tolerated


def _rot(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s], [s, c]])


def Polygon_circle(c, r):
    return Point(float(c[0]), float(c[1])).buffer(r, 24)


def incircle_fold(centre, apothem, corner, u, w):
    """Fold line of a spoke leaving a pentagon corner (Remy): perpendicular to the spoke's axis and tangent to the circle inscribed in
    the pentagon (the circle that touches its sides). `u` is the unit direction of the spoke away from the corner; the line crosses
    the axis at distance  apothem - (corner - centre).u  from the corner. Returns the two end points, w apart."""
    s = apothem - float((np.asarray(corner) - np.asarray(centre)) @ np.asarray(u))
    m = np.asarray(corner) + np.asarray(u) * s
    n = np.array([-u[1], u[0]])
    a, b = m + n * w / 2.0, m - n * w / 2.0
    return [[round(float(a[0]), 3), round(float(a[1]), 3)], [round(float(b[0]), 3), round(float(b[1]), 3)]]


class Patcher:
    def __init__(self, fr, w, D, f, maxp=5):
        self.fr, self.w, self.D, self.f = fr, w, D, f
        self.maxp = maxp                                  # most pentagons in one patch
        self.fp = min(f, fr.hole_diameter / 3.0)         # radius where a spoke meets a pentagon: never more than 1/3 of the polyp hole
        self._local = {}

    # ---- one part in its own plate plane -------------------------------------------------------
    def local(self, p):
        if p in self._local:
            return self._local[p]
        fr = self.fr
        V = fr.V
        plate = fr.polys[p]
        P3 = V[plate]; o = P3.mean(0); n = newell(P3)
        e1 = P3[0] - o; e1 = e1 - n * np.dot(e1, n); e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        q = {v: np.array([np.dot(V[v] - o, e1), np.dot(V[v] - o, e2)]) for v in plate}
        arms = []
        for v, w_ in fr.arms.get(p, []):
            d3 = V[w_] - V[v]
            h = float(np.dot(d3, n))
            qq = np.array([np.dot(d3, e1), np.dot(d3, e2)])
            if np.linalg.norm(qq) < 1e-6:
                qq = q[v]
            az = math.atan2(qq[1], qq[0])
            Ln = float(np.linalg.norm(d3))
            q[w_] = q[v] + Ln * np.array([math.cos(az), math.sin(az)])
            arms.append(dict(corner=v, far=w_, tilt=math.degrees(math.atan2(h, float(np.linalg.norm(qq)))), length=Ln))
        parts = [geom.plate_shape([tuple(q[v]) for v in plate])]
        for a in arms:
            parts.append(self.arm_shape(tuple(q[a["corner"]]), tuple(q[a["far"]]), False))
        L = dict(frame=(o, n, e1, e2), q=q, arms=arms, plate=list(plate), shape=unary_union(parts),
                 tip_of={a["far"]: a["corner"] for a in arms})
        self._local[p] = L
        return L

    def arm_shape(self, A, B, into_plate_at_far):
        """An arm from its plate corner A to its far node B. At A it carries straight on into the pentagon (no tip); at B it ends in
        a tip, or, if B is a corner of another pentagon in the patch, carries straight on into that one."""
        ux, uy = B[0] - A[0], B[1] - A[1]
        L = math.hypot(ux, uy) or 1e-9
        ux, uy = ux / L, uy / L
        k = 1.2 * self.w
        a2 = (A[0] - ux * k, A[1] - uy * k)
        b2 = (B[0] + ux * k, B[1] + uy * k) if into_plate_at_far else B
        return geom.spoke_shape(a2, b2, self.w, self.D, 0.0, ends=(False, not into_plate_at_far))

    def az3(self, p, d3):
        _, _, e1, e2 = self.local(p)["frame"]
        return math.atan2(float(np.dot(d3, e2)), float(np.dot(d3, e1)))

    # ---- placement -----------------------------------------------------------------------------
    def pos(self, p, T, node):
        rot, t = T[p]
        return _rot(rot) @ self.local(p)["q"][node] + t

    def connect(self, A, B, T):
        """Rigid placement (rot, t) of part B so that it joins the already placed part A, or None."""
        fr = self.fr
        LA, LB = self.local(A), self.local(B)
        for n in sorted(set(LA["q"]) & set(LB["q"])):
            cA, cB = LA["tip_of"].get(n), LB["tip_of"].get(n)
            if n in LB["plate"] and cA is not None:                      # A's arm ends on B's corner
                psi = math.atan2(*(self.pos(A, T, cA) - self.pos(A, T, n))[::-1])
                phi = self.az3(B, fr.V[cA] - fr.V[n])
            elif n in LA["plate"] and cB is not None:                    # B's arm ends on A's corner
                psi = self.az3(A, fr.V[cB] - fr.V[n]) + T[A][0]
                d = LB["q"][cB] - LB["q"][n]; phi = math.atan2(d[1], d[0])
            elif cA is not None and cB is not None:                      # both arms end on this node
                psiA = math.atan2(*(self.pos(A, T, cA) - self.pos(A, T, n))[::-1])
                nb = fr.ccw(n)
                s = 1.0 if (nb.index(cB) - nb.index(cA)) % len(nb) == 1 else -1.0
                psi = psiA + s * fr.angle3d(n, cA, cB)
                d = LB["q"][cB] - LB["q"][n]; phi = math.atan2(d[1], d[0])
            else:
                continue
            rot = psi - phi
            return rot, self.pos(A, T, n) - _rot(rot) @ LB["q"][n]
        return None

    def shape(self, p, T):
        rot, t = T[p]
        return affinity.translate(affinity.rotate(self.local(p)["shape"], rot, origin=(0, 0), use_radians=True), t[0], t[1])

    @staticmethod
    def fits(geometry):
        rect = geometry.minimum_rotated_rectangle
        xs, ys = rect.exterior.coords.xy
        a = math.hypot(xs[1] - xs[0], ys[1] - ys[0]); b = math.hypot(xs[2] - xs[1], ys[2] - ys[1])
        a, b = sorted((a, b))
        return a <= SHEET[0] and b <= SHEET[1], a, b

    # ---- growing patches -----------------------------------------------------------------------
    def grow(self, root, free):
        """One patch grown from `root` out of the plates in `free`. Returns (T, order, geometry dict)."""
        fr = self.fr
        T = {root: (0.0, np.zeros(2))}
        shapes = {root: self.shape(root, T)}
        order = [root]
        c0 = np.array(fr.info[root]["centre"])
        while len(order) < self.maxp:
            cands = []
            for B in free:
                if B in T:
                    continue
                for A in order:
                    if set(self.local(A)["q"]) & set(self.local(B)["q"]):
                        cands.append(B); break
            def rank(b):                                  # first the pentagons joined to this patch by a spoke between their corners (both then keep all their spokes), then arm-to-arm joints, then nearest
                direct = any(self.local(A)["tip_of"].get(n) is not None and n in self.local(b)["plate"] or self.local(b)["tip_of"].get(n) is not None and n in self.local(A)["plate"]
                             for A in order for n in set(self.local(A)["q"]) & set(self.local(b)["q"]))
                return (0 if direct else 1, float(np.linalg.norm(np.array(fr.info[b]["centre"]) - c0)))
            cands.sort(key=rank)
            added = False
            for B in cands:
                for A in order:
                    st = self.connect(A, B, T)
                    if st is None:
                        continue
                    T2 = dict(T); T2[B] = st
                    sh = self.shape(B, T2)
                    shared = [Point(*self.pos(B, T2, n)).buffer(self.D) for n in set(self.local(A)["q"]) & set(self.local(B)["q"])]
                    others = unary_union([shapes[x] for x in order])
                    over = sh.intersection(others)
                    if shared:
                        over = over.difference(unary_union(shared))
                    if over.area > OVERLAP_OK:
                        continue
                    ok, _, _ = self.fits(unary_union([others, sh]))
                    if not ok:
                        continue
                    T, shapes[B] = T2, sh
                    order.append(B)
                    added = True
                    break
                if added:
                    break
            if not added:
                break
        return T, order, shapes

    def partition(self, usable):
        free = sorted(usable)
        out, left = [], list(free)
        while left:
            T, order, shapes = self.grow(left[0], left)
            out.append(dict(T=T, order=order, shapes=shapes))
            left = [p for p in left if p not in T]
        return out

    # ---- what the page needs -------------------------------------------------------------------
    def payload(self, patch):
        fr, T, order = self.fr, patch["T"], patch["order"]
        parts, pos_of, bodies = [], {}, []
        corner_pos = {}
        for p_ in order:
            for v in self.local(p_)["plate"]:
                corner_pos[v] = self.pos(p_, T, v)
        for p in order:
            L = self.local(p)
            pos = {v: self.pos(p, T, v) for v in L["q"]}
            for v, xy in pos.items():
                pos_of.setdefault(v, xy)
            bodies.append(self.shape_plate_only(p, T))
            arms = []
            for a in L["arms"]:
                A, B = tuple(pos[a["corner"]]), tuple(pos[a["far"]])
                far = a["far"]
                into = far in corner_pos and float(np.linalg.norm(corner_pos[far] - np.array(B))) < 0.05
                bodies.append(self.arm_shape(A, B, into))
                u = (np.array(B) - np.array(A)); u = u / (np.linalg.norm(u) or 1.0)
                cen = {q_: np.mean([self.pos(q_, T, v) for v in self.local(q_)["plate"]], axis=0) for q_ in order}
                def apo(q_):
                    return float(np.mean([np.linalg.norm(self.pos(q_, T, v) - cen[q_]) for v in self.local(q_)["plate"]]) * math.cos(math.pi / 5))
                root = incircle_fold(cen[p], apo(p), A, u, self.w)
                if into:
                    q_ = next(x for x in order if far in self.local(x)["plate"])
                    farf = incircle_fold(cen[q_], apo(q_), B, -u, self.w)
                else:
                    farf = [[round(x, 3), round(y, 3)] for x, y in geom.fold_segments(A, B, self.w, self.D)[1]]
                arms.append(dict(corner=a["corner"], far=far, tilt=round(a["tilt"], 2), L=round(a["length"], 3), into=into,
                                 folds=[root, farf], a=[round(A[0], 3), round(A[1], 3)], b=[round(B[0], 3), round(B[1], 3)]))
            parts.append(dict(pent=p, plate=[[round(float(pos[v][0]), 3), round(float(pos[v][1]), 3)] for v in L["plate"]], plate_nodes=L["plate"], arms=arms))
        nodes = set(pos_of)
        ends = []
        for (a_, b_) in fr.loose:
            for v in (a_, b_):
                if v in nodes and not any(v in fr.polys[p] for p in order):
                    ends.append(dict(id=fr.loose_id[frozenset((a_, b_))], node=v, spine=False, xy=[round(float(pos_of[v][0]), 3), round(float(pos_of[v][1]), 3)]))
        for key in set(fr.spine_spokes) | set(fr.edge_spokes):
            for v in key:
                if v in nodes and v not in fr.band:
                    ends.append(dict(id=0, node=v, spine=True, xy=[round(float(pos_of[v][0]), 3), round(float(pos_of[v][1]), 3)]))
        body = self.body_shape(patch, bodies)
        U = unary_union([patch["shapes"][p] for p in order])
        ok, a, b = self.fits(body)
        return dict(parts=parts, body=geom.polys_of(body), ends=ends, size=dict(w=round(b, 2), h=round(a, 2), fits=ok), plates=order,
                    vertices=sorted(nodes), spokes=[[x["corner"], x["far"]] for pt in parts for x in pt["arms"]],
                    hole=fr.hole_diameter, w=self.w, D=self.D, f=self.f)

    def body_shape(self, patch, bodies=None):
        """The patch outline (shapely) with inside corners rounded, but only where a spoke meets a pentagon or where tips are
        (a rounding pass over the whole outline would also fill every window narrower than the rounding circle).
        Pentagon joins: radius min(f, 1/3 hole). Open-tip necks and spoke-to-spoke corners: radius f, built from just the spokes
        at that node."""
        if "body" in patch:
            return patch["body"]
        T, order = patch["T"], patch["order"]
        w, D, f, fp = self.w, self.D, self.f, self.fp
        R = geom.tip_radius(w, D)
        corner_pos = {v: self.pos(p_, T, v) for p_ in order for v in self.local(p_)["plate"]}
        plate_of = {v: p_ for p_ in order for v in self.local(p_)["plate"]}
        plates = {p_: geom.plate_shape([tuple(self.pos(p_, T, v)) for v in self.local(p_)["plate"]]) for p_ in order}
        base, fills = [], []
        corner_dirs = []                                   # (plate, corner xy, unit direction of the spoke leaving it)
        tips = {}
        for p in order:
            base.append(plates[p])
            for a in self.local(p)["arms"]:
                A, B = self.pos(p, T, a["corner"]), self.pos(p, T, a["far"])
                d = B - A; Ln = float(np.linalg.norm(d)); u = d / (Ln or 1.0)
                far = a["far"]
                into = far in corner_pos and float(np.linalg.norm(corner_pos[far] - B)) < 0.05
                base.append(self.arm_shape(tuple(A), tuple(B), into))
                corner_dirs.append((p, tuple(A), tuple(u)))
                if into:
                    corner_dirs.append((plate_of[far], tuple(B), tuple(-u)))
                else:
                    tips.setdefault((round(float(B[0]) / 0.05), round(float(B[1]) / 0.05)), (B, []))[1].append((-u, Ln))
        for pl, c, u in corner_dirs:                        # a spoke carrying straight on into a pentagon: round both inside corners
            loc = unary_union([plates[pl], geom.stub(c, u, w, 1.2 * w, 2.0 * w + 3.0 * fp)])
            fills.append(geom.blend(loc, fp).difference(loc))
        joints = []
        for B, items in tips.values():                      # a free tip: round the necks; two or more spokes on one node: round the corners between them
            loc = [Polygon_circle(B, R)]
            for u, Ln in items:
                ell = min(Ln, 2 * f + 2 * R + w)
                loc.append(geom.spoke_shape(tuple(B), tuple(B + u * ell), w, D, 0.0, ends=(True, False)))
            loc = unary_union(loc)
            fills.append(geom.blend(loc, f).difference(loc))
            if len(items) >= 2:
                joints.append((tuple(B), [tuple(u) for u, _ in items]))
        fills += geom.junction_fillers(joints, w, D, f)
        patch["body"] = unary_union(base + fills)
        return patch["body"]

    def shape_plate_only(self, p, T):
        rot, t = T[p]
        poly = geom.plate_shape([tuple(self.pos(p, T, v)) for v in self.local(p)["plate"]])
        return poly
