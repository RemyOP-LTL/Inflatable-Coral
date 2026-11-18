"""Packs the cut pieces close together for the laser (the Detailed view keeps its own easy-to-read layout).

How it works, in plain language: every piece is drawn as a picture on a coarse grid (3 mm squares), grown by half the gap you ask for.
The biggest piece goes in the top-left corner. Each next piece is tried at every turn from 0 to 345 degrees in 15 degree steps and
at every spot where it does not touch what is already placed; the spot and turn that make the whole group's bounding box
smallest win. (The "does it touch" test for every spot at once is a correlation done with FFTs, which is quick.)
Pieces are only turned, never flipped. The result is a turn and a shift for each piece; the real, un-gridded outlines are
then moved by that, and checked to be at least the gap apart.
"""
import math
import numpy as np
from matplotlib.path import Path
from shapely import affinity
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid

RES = 3.0                       # grid square size in mm
ANGLES = list(range(0, 360, 15))


def _as_geometry(points):
    """A solid shape from a closed outline (the frill outline doubles back along its slits, so clean it up first)."""
    g = make_valid(Polygon(np.asarray(points, float)))
    return g.buffer(0.3)


def _mask(geom, pad):
    """Boolean picture of geom (already shifted so its lower-left corner is at (pad, pad)) on the RES grid."""
    minx, miny, maxx, maxy = geom.bounds
    w = int(math.ceil((maxx + pad) / RES)) + 1
    h = int(math.ceil((maxy + pad) / RES)) + 1
    xs = (np.arange(w) + 0.5) * RES
    ys = (np.arange(h) + 0.5) * RES
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    inside = np.zeros(len(pts), dtype=bool)
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        inside |= Path(np.array(p.exterior.coords)).contains_points(pts)
        for hole in p.interiors:
            inside &= ~Path(np.array(hole.coords)).contains_points(pts)
    return inside.reshape(h, w)


def nest(shapes, gap):
    """shapes: {name: list of closed outline points}. Returns {name: (angle in degrees, tx, ty)}: a point p of that piece
    goes to rotate(p, angle about the origin) + (tx, ty)."""
    geoms = {n: _as_geometry(p) for n, p in shapes.items()}
    order = sorted(geoms, key=lambda n: -geoms[n].area)
    grow = gap / 2 + RES * 0.6                                   # half the gap plus a little for the grid
    pad = grow + RES
    total = sum(g.area for g in geoms.values())
    biggest = max(max(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1]) for g in geoms.values())
    side = max(biggest * 2.3, math.sqrt(total) * 2.2) + 4 * pad
    Hc = Wc = int(math.ceil(side / RES))
    placed = np.zeros((Hc, Wc), dtype=float)
    ext = None                                                   # bounding box of everything placed, in cells: (minx, maxx, miny, maxy)
    result = {}
    for k, name in enumerate(order):
        base = geoms[name]
        best = None
        angs = [0] if k == 0 else ANGLES
        for ang in angs:
            g = affinity.rotate(base, ang, origin=(0, 0))
            mnx, mny = g.bounds[0], g.bounds[1]
            g = affinity.translate(g, pad - mnx, pad - mny)
            m = _mask(g.buffer(grow), pad)
            h, w = m.shape
            if h > Hc or w > Wc:
                continue
            if k == 0:
                ys, xs = np.array([0]), np.array([0])
            else:
                shape = (Hc + h, Wc + w)
                corr = np.fft.irfft2(np.fft.rfft2(placed, shape) * np.conj(np.fft.rfft2(m.astype(float), shape)), shape)
                ok = corr[:Hc - h + 1, :Wc - w + 1] < 0.5
                ys, xs = np.nonzero(ok)
                if len(ys) == 0:
                    continue
            if ext is None:
                nminx, nmaxx, nminy, nmaxy = xs, xs + w, ys, ys + h
            else:
                nminx = np.minimum(ext[0], xs); nmaxx = np.maximum(ext[1], xs + w)
                nminy = np.minimum(ext[2], ys); nmaxy = np.maximum(ext[3], ys + h)
            bw, bh = nmaxx - nminx, nmaxy - nminy
            score = bw * bh + 4.0 * (bw + bh) + 0.01 * (ys + xs)            # smallest bounding box; then a little preference for the top-left
            i = int(np.argmin(score))
            if best is None or score[i] < best[0]:
                best = (float(score[i]), ang, int(xs[i]), int(ys[i]), h, w, m, (int(nminx[i]) if ext is not None else int(xs[i]),
                        int(nmaxx[i]), int(nminy[i]), int(nmaxy[i])), mnx, mny)
        if best is None:
            raise RuntimeError("could not place " + name)
        _, ang, ix, iy, h, w, m, ext, mnx, mny = best
        placed[iy:iy + h, ix:ix + w] = np.maximum(placed[iy:iy + h, ix:ix + w], m.astype(float))
        # real outline: rotate, bring its lower-left to (pad, pad), then to the grid cell (ix, iy)
        tx = ix * RES + pad - mnx
        ty = iy * RES + pad - mny
        result[name] = (float(ang), float(tx), float(ty))
    return compact(shapes, result, gap, order)


def compact(shapes, transforms, gap, order):
    """Slide each piece (not the first) left and up, 2 mm at a time and then finer, until it is the requested gap from its
    neighbours. This works on the real outlines, so it removes the slack the coarse grid left."""
    need = max(gap - 0.3, 0.2)                                   # the outlines used here are grown 0.3 mm and simplified by up to 0.3 mm
    geo = {n: _as_geometry(apply(shapes[n], transforms[n])).simplify(0.3) for n in shapes}
    tr = {n: list(v) for n, v in transforms.items()}
    others = lambda n: [g for m, g in geo.items() if m != n]

    allb = [g.bounds for g in geo.values()]
    box = (min(b[0] for b in allb), min(b[1] for b in allb))        # top-left corner of the group: pieces may not slide beyond it, so the group never grows

    def free(n, g):
        b = g.bounds
        if b[0] < box[0] - 1e-6 or b[1] < box[1] - 1e-6:
            return False
        return all(g.distance(o) >= need for o in others(n))

    for _ in range(3):
        moved = False
        for n in order[1:]:
            for dx, dy in ((-1, 0), (0, -1), (-1, -1), (-1, 1), (1, -1)):
                if dx > 0 or (dy > 0):
                    continue                                       # only slide toward the top-left
                step, t_ok = 2.0, 0.0
                while t_ok < 400:
                    g = affinity.translate(geo[n], dx * (t_ok + step), dy * (t_ok + step))
                    if not free(n, g):
                        break
                    t_ok += step
                lo, hi = t_ok, t_ok + step                         # refine the last step
                for _ in range(5):
                    mid = (lo + hi) / 2
                    if free(n, affinity.translate(geo[n], dx * mid, dy * mid)):
                        lo = mid
                    else:
                        hi = mid
                if lo > 0.05:
                    geo[n] = affinity.translate(geo[n], dx * lo, dy * lo)
                    tr[n][1] += dx * lo
                    tr[n][2] += dy * lo
                    moved = True
        if not moved:
            break
    return {n: tuple(v) for n, v in tr.items()}


def apply(points, transform):
    ang, tx, ty = transform
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    p = np.asarray(points, float)
    return np.column_stack([p[:, 0] * c - p[:, 1] * s + tx, p[:, 0] * s + p[:, 1] * c + ty])
