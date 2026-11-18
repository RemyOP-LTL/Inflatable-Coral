#!/usr/bin/env python3
"""
The 3D model for the page (Remy, 2026-11-16). Spokes can flex and twist but not stretch: each spoke is ONE solid piece (strip
and both tip circles) laid straight between its two nodes, twisting to follow the surface normal at each end. Pentagon plates
are flat; every spoke that meets a plate continues straight into it and the corner is rounded with the transition radius.
The spine is one piece laid on the surface along the curve.
Open-spoke tips (the free ends of the arms) that overlap another spoke are marked, for the page to draw red.
Needs numpy and shapely.
"""
import math

import numpy as np
import shapely
from shapely import constrained_delaunay_triangles
from shapely.geometry import MultiPoint, Point
from shapely.ops import unary_union

import geom
from frame import newell

T = 0.14                  # thickness drawn for the plastic, inches


def tri_mesh(poly):
    idx, V, F = {}, [], []
    for t in constrained_delaunay_triangles(poly).geoms:
        f = []
        for x, y in list(t.exterior.coords)[:3]:
            k = (round(x, 4), round(y, 4))
            if k not in idx:
                idx[k] = len(V); V.append(k)
            f.append(idx[k])
        F.append(f)
    return V, F


def _r(a):
    return np.round(np.asarray(a, float), 2).ravel().tolist()


def spoke_ribbon(fr, a, b, w, D, f, ends, red_tip, B_override=None):
    A, B = fr.V[a], (fr.V[b] if B_override is None else B_override)
    d = B - A
    L = float(np.linalg.norm(d))
    u = d / L
    V2, F = tri_mesh(geom.spoke_shape((0.0, 0.0), (L, 0.0), w, D, f, ends=ends))
    nA, nB = fr.vnorm[a], fr.vnorm[b]
    P, red = [], []
    R = geom.tip_radius(w, D)
    for i, (x, y) in enumerate(V2):
        tau = min(max(x / L, 0.0), 1.0)
        n = (1 - tau) * nA + tau * nB
        n = n - u * float(np.dot(n, u))
        n /= np.linalg.norm(n) or 1.0
        P.append(A + u * x + np.cross(n, u) * y + n * T / 2)
        if red_tip and ends[1] and math.hypot(x - L, y) <= R + 1e-3:
            red.append(i)
    return dict(v=_r(P), t=[k for tri in F for k in tri], red=red)


def tessellate(poly, spacing=0.4):
    """Triangles filling a flat polygon (with holes), with points inside as well as on the edge so it can bend when wrapped."""
    seg = shapely.segmentize(poly, spacing * 0.7)
    pts = []
    for g in getattr(seg, "geoms", [seg]):                  # segmentize can return several polygons for a pinched outline
        if g.geom_type == "Polygon":
            for ring in [g.exterior] + list(g.interiors):
                pts += list(ring.coords)[:-1]
    minx, miny, maxx, maxy = poly.bounds
    X, Y = np.meshgrid(np.arange(minx, maxx, spacing), np.arange(miny, maxy, spacing))
    X, Y = X.ravel(), Y.ravel()
    ok = shapely.contains_xy(poly.buffer(-spacing * 0.45), X, Y)
    pts += list(zip(X[ok], Y[ok]))
    pts = list(dict.fromkeys((round(x, 4), round(y, 4)) for x, y in pts))
    if len(pts) < 3:
        return np.zeros((0, 2)), []
    idx = {p: i for i, p in enumerate(pts)}
    tris = list(shapely.delaunay_triangles(MultiPoint(pts)).geoms)
    cx = np.array([t.centroid.x for t in tris]); cy = np.array([t.centroid.y for t in tris])
    inside = shapely.contains_xy(poly, cx, cy)
    F = [[idx[(round(x, 4), round(y, 4))] for x, y in list(t.exterior.coords)[:3]] for t, k in zip(tris, inside) if k]
    return np.array(pts), F


def patch_mesh(fr, pt, patch, w, D, f, hole):
    """One patch as it is laid flat (rounded outline), wrapped onto the surface: each piece of the flat outline moves with the
    part it belongs to. Plates stay flat; each arm is a straight strip between its two nodes, twisting with the surface."""
    from patches import _rot
    T, order = patch["T"], patch["order"]
    body = pt.body_shape(patch)
    holes = [Point(*np.mean([pt.pos(p, T, v) for v in pt.local(p)["plate"]], axis=0)).buffer(hole / 2.0, 32) for p in order]
    body = body.difference(unary_union(holes))
    # pieces: plates and arms
    plates, arms = [], []
    for p in order:
        L = pt.local(p)
        o, n, e1, e2 = L["frame"]
        rot, t = T[p]
        flat = [pt.pos(p, T, v) for v in L["plate"]]
        plates.append(dict(id=p, poly=geom.plate_shape([tuple(x) for x in flat]), R=_rot(rot), t=t, o=o, n=n, e1=e1, e2=e2))
        for a in L["arms"]:
            A, B = pt.pos(p, T, a["corner"]), pt.pos(p, T, a["far"])
            arms.append(dict(a=A, b=B, A3=fr.V[a["corner"]], B3=fr.V[a["far"]], nA=fr.vnorm[a["corner"]], nB=fr.vnorm[a["far"]],
                             tip=a["far"], corner=a["corner"]))
    Vout, Fout, pid, red = [], [], [], []
    R = geom.tip_radius(w, D)
    red_centres = []
    for arm in arms:
        far = arm["tip"]
        into = any(far in pt.local(q)["plate"] for q in order) and any(np.linalg.norm(pt.pos(q, T, far) - arm["b"]) < 0.05 for q in order if far in pt.local(q)["plate"])
        if not into and any(x != arm["corner"] and frozenset((far, x)) not in {frozenset(e) for q in fr.part["plates"] for e in zip(fr.polys[q], fr.polys[q][1:] + fr.polys[q][:1])} for x in fr.adj[far]):
            red_centres.append(arm["b"])
    for geo in getattr(body, "geoms", [body]):
        if geo.geom_type != "Polygon" or geo.area < 1e-3:
            continue
        P, F = tessellate(geo)
        if not len(P):
            continue
        pts = shapely.points(P)
        best = np.full(len(P), np.inf); piece = np.zeros(len(P), int)
        for k, pl in enumerate(plates):
            d = shapely.distance(pl["poly"], pts)
            better = d < best - 1e-9
            best = np.where(better, d, best); piece = np.where(better, k, piece)
        for j, arm in enumerate(arms):
            ab = arm["b"] - arm["a"]; L2 = float(ab @ ab) or 1e-9
            tt = np.clip(((P - arm["a"]) @ ab) / L2, 0, 1)
            d = np.linalg.norm(P - (arm["a"] + tt[:, None] * ab), axis=1) - w / 2.0
            d = np.maximum(d, 0.0) + 2e-3                     # a plate wins a tie
            better = d < best - 1e-9
            best = np.where(better, d, best); piece = np.where(better, len(plates) + j, piece)
        P3 = np.zeros((len(P), 3)); ids = np.full(len(P), -1)
        for k, pl in enumerate(plates):
            sel = piece == k
            if sel.any():
                loc = (pl["R"].T @ (P[sel] - pl["t"]).T).T
                P3[sel] = pl["o"] + np.outer(loc[:, 0], pl["e1"]) + np.outer(loc[:, 1], pl["e2"]) + pl["n"] * T_ * 0.6
                ids[sel] = pl["id"]
        for j, arm in enumerate(arms):
            sel = piece == len(plates) + j
            if not sel.any():
                continue
            ab = arm["b"] - arm["a"]; Ln = float(np.linalg.norm(ab)) or 1e-9
            uf = ab / Ln; nf = np.array([-uf[1], uf[0]])
            s = (P[sel] - arm["a"]) @ uf; tt = (P[sel] - arm["a"]) @ nf
            u3 = (arm["B3"] - arm["A3"]); u3 = u3 / np.linalg.norm(u3)
            tau = np.clip(s / Ln, 0, 1)[:, None]
            nn = (1 - tau) * arm["nA"] + tau * arm["nB"]
            nn = nn - np.outer(nn @ u3, u3); nn /= np.linalg.norm(nn, axis=1)[:, None]
            P3[sel] = arm["A3"] + np.outer(s, u3) + np.cross(nn, u3) * tt[:, None] + nn * T_ / 2
        base = len(Vout)
        Vout += P3.tolist(); pid += ids.tolist(); Fout += [[base + i for i in tri] for tri in F]
        for c in red_centres:
            red += [base + int(i) for i in np.where(np.linalg.norm(P - c, axis=1) <= R + 0.02)[0]]
    return dict(v=_r(Vout), t=[k for tri in Fout for k in tri], pid=pid, red=red, plates=order)


T_ = T


def plate_body(fr, p, w, D, f, hole):
    """The flat plate, with a stub where each corner's spoke leaves, rounded; minus the polyp hole. As (verts, tris) in 3D."""
    P3 = fr.V[fr.polys[p]]
    o = P3.mean(0); n = newell(P3)
    e1 = P3[0] - o; e1 = e1 - n * np.dot(e1, n); e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    q = {v: (float(np.dot(fr.V[v] - o, e1)), float(np.dot(fr.V[v] - o, e2))) for v in fr.polys[p]}
    shape = geom.plate_shape([q[v] for v in fr.polys[p]])
    parts = [shape]
    for v in fr.polys[p]:
        out = [x for x in fr.adj[v] if x not in fr.polys[p]]
        for x in out:
            d3 = fr.V[x] - fr.V[v]
            dxy = (float(np.dot(d3, e1)), float(np.dot(d3, e2)))
            if math.hypot(*dxy) > 1e-6:
                parts.append(geom.stub(q[v], dxy, w, 1.2 * w, 1.0 * w))
    body = geom.blend(unary_union(parts), f)
    cx, cy = float(np.mean([a[0] for a in q.values()])), float(np.mean([a[1] for a in q.values()]))
    body = body.difference(Point(cx, cy).buffer(hole / 2.0, 24))
    if body.geom_type != "Polygon":
        body = max(body.geoms, key=lambda g: g.area)
    V2, F = tri_mesh(body)
    P = [o + e1 * x + e2 * y + n * T * 0.6 for x, y in V2]
    return dict(v=_r(P), t=[k for tri in F for k in tri])


def build(fr, curve, w, D, f, hole, pt=None, res=()):
    D = max(D, w)
    fp = min(f, hole / 3.0)
    patch_meshes = [patch_mesh(fr, pt, r, w, D, f, hole) for r in res] if pt is not None else []
    in_patch = {p for r in res for p in r["order"]}
    in_patch_arms = {frozenset(e) for p in in_patch for e in fr.arms.get(p, [])}
    plates = {}
    for p, s in enumerate(fr.sides):
        if s == 5 and not fr.on_spine[p] and p not in in_patch:
            plates[p] = plate_body(fr, p, w, D, fp, hole)
    corners = {v for p in plates for v in fr.polys[p]}
    plate_sides = {frozenset(e) for p in plates for e in zip(fr.polys[p], fr.polys[p][1:] + fr.polys[p][:1])}
    arm_owner = {frozenset((v, x)): p for p, arms in fr.arms.items() for v, x in arms}
    spokes = []
    for e, ps in fr.edge_polys.items():
        if e in plate_sides or fr.hidden(e) or e in fr.spine_spokes or e in fr.edge_spokes or e in in_patch_arms:
            continue
        a, b = sorted(e)
        kind = "ext" if all(fr.end[p] for p in ps) else ("loose" if e in fr.loose_id else "arm")
        # an arm leaves its plate corner (no tip there) and ends either free (tip) or on another plate's corner (no tip)
        arm = arm_owner.get(e)
        ends = (True, True)
        red_tip = False
        if arm is not None:
            root = next(v for v in e if v in fr.polys[arm])
            far = a if root == b else b
            tip_far = far not in corners
            ends = (False, tip_far) if root == a else (tip_far, False)
            red_tip = tip_far
        else:
            ends = (a not in corners, b not in corners)
        # the free-tip end of an arm is the one that is True; make the ribbon run root -> far so 'ends[1]' is the tip
        if arm is not None:
            if root != a:
                a, b = b, a
            ends = (False, tip_far)
        rb = spoke_ribbon(fr, a, b, w, D, f, ends, False)
        rb.update(a=int(a), b=int(b), kind=kind, owner=arm, tip=(bool(ends[1]) if arm is not None else None))
        spokes.append(rb)
    Rr = geom.tip_radius(w, D)
    for t in fr.layout.get("spine", {}).get("edges", []) if fr.spine else []:             # longer spokes from a node to the spine edge, tip overlapping the spine
        e, n = t["edge"], t["node"]
        u = fr.V[e] - fr.V[n]; u = u / np.linalg.norm(u)
        Q = fr.V[e] + u * Rr
        if curve is not None:
            Q = curve.surface.snap(Q[None, :])[0]
        rb = spoke_ribbon(fr, n, e, w, D, f, (True, True), False, B_override=Q)
        rb.update(a=int(n), b=int(e), kind="edge", owner=None, tip=None)
        spokes.append(rb)
    # rivet points: every node where two or more spokes meet (not a pentagon corner, where a spoke runs straight on into the plate)
    deg = {}
    for e_, ps_ in fr.edge_polys.items():
        if e_ in plate_sides or fr.hidden(e_):
            continue
        for v in e_:
            deg[v] = deg.get(v, 0) + 1
    riv = [dict(p=_r(fr.V[v] + fr.vnorm[v] * (T * 2.2 + 0.06)), n=_r(fr.vnorm[v])) for v, k in deg.items() if k >= 2 and v not in corners and v not in fr.band]
    for t in fr.layout.get("spine", {}).get("edges", []) if fr.spine else []:
        e, n = t["edge"], t["node"]
        u = fr.V[e] - fr.V[n]; u = u / np.linalg.norm(u)
        Q = fr.V[e] + u * Rr
        riv.append(dict(p=_r(Q + fr.vnorm[e] * (T * 2.2 + 0.06)), n=_r(fr.vnorm[e])))
    out = dict(plates={str(p): m for p, m in plates.items()}, spokes=spokes, patches=patch_meshes, rivets=riv, rivet_r=round(Rr * 0.9, 3), T=T)
    if fr.spine and curve is not None:
        import spine as SP
        shape, _, _ = geom.spine_shape(fr.spine, w, D, f)
        pts2, tris = SP.outline_mesh(shape)
        p2 = np.array(pts2)
        P = curve.to3d(p2[:, 0], p2[:, 1])
        n = np.array([curve.n[min(int(np.searchsorted(curve.s, s_)), len(curve.s) - 1)] for s_ in p2[:, 0]])
        out["spine"] = dict(v=_r(P + n * T * 0.5), t=[k for tri in tris for k in tri])
    return out
