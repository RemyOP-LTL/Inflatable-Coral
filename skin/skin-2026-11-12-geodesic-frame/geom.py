#!/usr/bin/env python3
"""
Shapes of the plastic pieces (inches). Needs shapely.

SPOKE: a strip of width w with a round tip of diameter D at each end (D >= w; D == w is a thick line with a dot).
Where the tip meets the strip the corner is rounded with radius f (the "transition radius"). The rounding is a
closing (grow by f, shrink by f), which puts a radius-f arc tangent to both the strip edge and the tip circle.

FOLD LINE: across the strip, between the two points where the tip circle meets the strip's edges, measured BEFORE
the corner is rounded. Its distance from the tip centre is sqrt(R^2 - (w/2)^2) with R = D/2.
"""
import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

SEG = 12     # segments per quarter circle


def tip_radius(w, D):
    return max(D, w) / 2.0


def fold_offset(w, D):
    R, h = tip_radius(w, D), w / 2.0
    return math.sqrt(max(R * R - h * h, 0.0))


def spoke_shape(a, b, w, D, f, ends=(True, True)):
    """Shapely polygon of the spoke from node a to node b (each an (x, y)). `ends` says which ends carry a tip."""
    R, h = tip_radius(w, D), w / 2.0
    (ax, ay), (bx, by) = a, b
    L = math.hypot(bx - ax, by - ay) or 1e-9
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = -uy, ux
    rect = Polygon([(ax + nx * h, ay + ny * h), (bx + nx * h, by + ny * h), (bx - nx * h, by - ny * h), (ax - nx * h, ay - ny * h)])
    parts = [rect]
    if ends[0]:
        parts.append(Point(ax, ay).buffer(R, SEG))
    if ends[1]:
        parts.append(Point(bx, by).buffer(R, SEG))
    shape = unary_union(parts)
    if f > 1e-6 and R > h + 1e-6:
        shape = shape.buffer(f, SEG).buffer(-f, SEG)
    return shape


def fold_segments(a, b, w, D):
    """The fold line at each end of a spoke a-b, as ((x1, y1), (x2, y2)) pairs, one near a, one near b."""
    h, x0 = w / 2.0, fold_offset(w, D)
    (ax, ay), (bx, by) = a, b
    L = math.hypot(bx - ax, by - ay) or 1e-9
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = -uy, ux
    out = []
    for (px, py, sx, sy) in ((ax, ay, ux, uy), (bx, by, -ux, -uy)):
        cx, cy = px + sx * x0, py + sy * x0
        out.append(((cx + nx * h, cy + ny * h), (cx - nx * h, cy - ny * h)))
    return out


def coords(poly):
    """Exterior ring as a list of [x, y], rounded for sending to the page."""
    return [[round(x, 3), round(y, 3)] for x, y in list(poly.exterior.coords)[:-1]]


def plate_shape(corners):
    return Polygon(corners)


def stub(corner, direction_xy, w, back, ahead):
    """A rectangle of width w across a spoke's direction at a plate corner: it runs `back` into the plate and `ahead` out of it.
    Joined to the plate and rounded (see blend), it makes the spoke continue straight into the pentagon."""
    cx, cy = corner
    ux, uy = direction_xy
    L = math.hypot(ux, uy) or 1.0
    ux, uy = ux / L, uy / L
    nx, ny = -uy, ux
    h = w / 2.0
    a = (cx - ux * back, cy - uy * back)
    b = (cx + ux * ahead, cy + uy * ahead)
    return Polygon([(a[0] + nx * h, a[1] + ny * h), (b[0] + nx * h, b[1] + ny * h), (b[0] - nx * h, b[1] - ny * h), (a[0] - nx * h, a[1] - ny * h)])


def blend(shape, f):
    """Round every inside corner with radius f (grow by f, shrink by f)."""
    if f > 1e-6:
        shape = shape.buffer(f, SEG).buffer(-f, SEG)
    return shape


def polys_of(shape, simplify=0.01):
    """A shapely shape as a list of {ext, holes} rings for the page."""
    if shape.is_empty:
        return []
    out = []
    for g in getattr(shape, "geoms", [shape]):
        if g.geom_type != "Polygon":
            continue
        g = g.simplify(simplify)
        out.append(dict(ext=[[round(x, 3), round(y, 3)] for x, y in list(g.exterior.coords)[:-1]],
                        holes=[[[round(x, 3), round(y, 3)] for x, y in list(r.coords)[:-1]] for r in g.interiors]))
    return out


def spine_shape(sp, w, D, f):
    """The spine piece: the strip (with its lobes) plus every spine spoke, blended into the edge with radius f.
    Returns (shape, hole centres, fold segments) in (sigma, u)."""
    from shapely.ops import unary_union
    pieces, holes, folds = [Polygon(sp["outline"])], [], []
    for t in sp.get("tabs", []):
        dx, dy = t["dir"]
        E = (t["sigma"] - dx * 1.2, t["u"] - dy * 1.2)
        N = (t["sigma"] + dx * t["L"], t["u"] + dy * t["L"])
        pieces.append(spoke_shape(E, N, w, D, f, ends=(False, True)))
        holes.append([round(N[0], 3), round(N[1], 3)])
        folds.append([[round(x, 3), round(y, 3)] for x, y in fold_segments((t["sigma"], t["u"]), N, w, D)[1]])
    R = tip_radius(w, D)
    for t in sp.get("edges", []):                    # an edge spoke's tip centre lies R inside the spine edge, on the spoke's axis
        holes.append([round(t["sigma"] + t["dir"][0] * R, 3), round(t["u"] + t["dir"][1] * R, 3)])
    shape = blend(unary_union(pieces), f)
    if shape.geom_type != "Polygon":
        shape = max(shape.geoms, key=lambda g: g.area)
    return shape, holes, folds


def junction_fillers(joints, w, D, f):
    """Where two spokes meet at a node (both tips on the same circle), their straight edges can run into each other inside that
    circle. Then the corner between them is rounded with the radius whose circle is tangent to both straight edges AND to the
    node circle (Remy's rule), if that is bigger than the ordinary neck radius f. joints = [(node_xy, [unit vectors away from the node])].
    Returns shapes to add."""
    R, h = tip_radius(w, D), w / 2.0
    out = []
    for n, dirs in joints:
        if len(dirs) < 2:
            continue
        ang = sorted(math.atan2(d[1], d[0]) for d in dirs)
        for i in range(len(ang)):
            a1, a2 = ang[i], ang[(i + 1) % len(ang)]
            theta = (a2 - a1) % (2 * math.pi)
            if theta >= math.pi - 1e-6 or theta < 1e-3:
                continue
            s = math.sin(theta / 2)
            if R * s - h <= 1e-9:                 # the edges meet outside the circle: the ordinary rounding does it
                continue
            r = (R * s - h) / (1 - s)
            if r <= f:
                continue
            u1, u2 = (math.cos(a1), math.sin(a1)), (math.cos(a2), math.sin(a2))
            bx, by = u1[0] + u2[0], u1[1] + u2[1]
            bl = math.hypot(bx, by) or 1.0
            bx, by = bx / bl, by / bl
            A = (n[0] + bx * h / s, n[1] + by * h / s)             # where the two straight edges would meet
            c = (A[0] + bx * r / s, A[1] + by * r / s)             # centre of the rounding
            tl = r / math.tan(theta / 2)
            T1 = (A[0] + u1[0] * tl, A[1] + u1[1] * tl)
            T2 = (A[0] + u2[0] * tl, A[1] + u2[1] * tl)
            out.append(Polygon([A, T1, c, T2]).difference(Point(c).buffer(r, 48)))
    return out


def finish(base, f_open, f_pent, corners, rho, fillers=()):
    """Round the inside corners of a patch outline: radius f_open everywhere (open-tip necks, spoke-to-spoke corners), but only
    f_pent (never more than a third of the polyp hole) within rho of a pentagon corner, where a spoke runs into a pentagon."""
    from shapely.ops import unary_union
    S = unary_union([base] + list(fillers))
    closed = lambda f: S.buffer(f, SEG).buffer(-f, SEG) if f > 1e-6 else S
    near = unary_union([Point(c).buffer(rho, 24) for c in corners]) if corners else Polygon()
    far = closed(f_open).difference(S).difference(near)
    nr = closed(f_pent).difference(S).intersection(near) if corners else Polygon()
    return unary_union([S, far, nr])
