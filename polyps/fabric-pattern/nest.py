"""Pack copies of one cut piece (and its mirror image) tightly onto a sheet, for the laser cutter.

Only two moves are allowed, because the fabric has a grain that runs along the finger: a piece may be turned
180 degrees (the grain still runs the same way), and the mirror-image pieces are flipped sideways (same).
So each piece has two possible positions.

How it works: every piece is drawn on a fine grid (0.05 in). For each new piece the program finds every grid
position where it fits without touching what is already placed (leaving a gap for the laser), and picks the
one that touches the most already-placed fabric or sheet edge while keeping the layout short. That makes pieces
snuggle into each other's hollows. It repeats this for several sheet widths, settings and orders (a fixed, seeded
list, so the answer is the same every time) and keeps the smallest layout.
Needs only numpy, scipy and shapely.
"""
import random

import numpy as np
from matplotlib.path import Path
from scipy.ndimage import binary_dilation
from scipy.signal import fftconvolve
from shapely.geometry import Polygon

RES = 0.05                                   # grid cell, inches
PAD = 8                                      # cells of "wall" outside the sheet, so touching an edge counts as contact
MAX_HEIGHT = 70.0                            # tallest layout the grid can hold, inches
AUTO_WIDTHS = (16, 18, 19, 20, 21, 22, 24)
SETTINGS = ((20, 4), (40, 2))                # (weight on keeping it short, how far "touching" reaches in cells)


def _mask(poly, gap):
    """Grid cells (rows = y, columns = x) touched by `poly` fattened by half the gap. Two pieces whose masks
    share no cell are at least `gap` apart. Returns the mask and the position of its corner."""
    fat = poly.buffer(gap / 2 + RES * 0.72)
    x0, y0, x1, y1 = fat.bounds
    nx, ny = int(np.ceil((x1 - x0) / RES)) + 1, int(np.ceil((y1 - y0) / RES)) + 1
    xs = x0 + (np.arange(nx) + 0.5) * RES
    ys = y0 + (np.arange(ny) + 0.5) * RES
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    inside = np.zeros(gx.shape, bool)
    for ring in [fat.exterior] + list(fat.interiors):
        inside ^= Path(np.asarray(ring.coords)).contains_points(pts).reshape(gx.shape)
    return inside, (x0, y0)


def _pack(ring, order, width, gap, weight, reach, cache):
    """One packing run on a sheet `width` inches wide. `order` lists, piece by piece, whether it is a mirror
    image. Returns the placements [(sx, sy, dx, dy)] or None if something doesn't fit."""
    cols = int(round(width / RES))
    rows_all = int(MAX_HEIGHT / RES)
    occ = np.zeros((rows_all, cols), bool)
    top = 0
    placements = []
    for mirrored in order:
        flips = ((-1, 1), (1, -1)) if mirrored else ((1, 1), (-1, -1))
        for f in flips:
            if f not in cache:
                cache[f] = _mask(Polygon(ring * list(f)), gap)
        tallest = max(cache[f][0].shape[0] for f in flips)
        rows = min(rows_all, top + tallest)
        ext = np.zeros((rows + PAD, cols + 2 * PAD), bool)           # the layout so far, with walls around it
        ext[PAD:, PAD:PAD + cols] = occ[:rows]
        ext[:PAD, :] = True
        ext[:, :PAD] = True
        ext[:, PAD + cols:] = True
        near = binary_dilation(ext, iterations=reach).astype(float)
        best = None
        for f in flips:
            m, (cx, cy) = cache[f]
            hm, wm = m.shape
            if wm > cols or hm > rows:
                continue
            flipped = m[::-1, ::-1].astype(float)
            hit = fftconvolve(occ[:rows], flipped, mode="valid")
            ys, xs = np.nonzero(hit < 0.5)                           # positions that don't touch anything
            if len(ys) == 0:
                continue
            contact = fftconvolve(near, flipped, mode="valid")[PAD + ys, PAD + xs]
            new_top = np.maximum(top, ys + hm)
            score = contact - weight * new_top - 1e-3 * ys
            k = int(np.argmax(score))
            if best is None or score[k] > best[0]:
                best = (score[k], int(new_top[k]), int(ys[k]), int(xs[k]), f, cx, cy, m)
        if best is None:
            return None
        _, top, iy, ix, f, cx, cy, m = best
        occ[iy:iy + m.shape[0], ix:ix + m.shape[1]] |= m
        # the mask's corner sits at (cx, cy) in the flipped piece's own coordinates, and it goes to grid cell (ix, iy)
        placements.append((f[0], f[1], ix * RES - cx, iy * RES - cy))
    return placements


def nest_pieces(ring, n_each, gap=0.125, bed=None, max_side=48.0):
    """Lay out `n_each` pieces and `n_each` mirror images for cutting.
      bed = (width, length) of the laser bed in inches (length is along the grain), or None for no bed
      max_side = with no bed, the longest side allowed
    Returns a dict: placements [(sx, sy, dx, dy)] (flip signs and shift for each piece), size (w, h) of the
    layout, fill (fraction of it that is fabric) and min_gap (closest two pieces come, in inches)."""
    ring = np.asarray(ring, float)
    if np.allclose(ring[0], ring[-1]):
        ring = ring[:-1]
    area = Polygon(ring).area
    n = 2 * n_each
    rng = random.Random(2026)
    orders = [[bool(i % 2) for i in range(n)]]
    for _ in range(2):
        o = [True] * n_each + [False] * n_each
        rng.shuffle(o)
        orders.append(o)
    if bed:
        limit_w, limit_l = bed
        widths = sorted({round(limit_w * f, 1) for f in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75)}, reverse=True)
    else:
        limit_w = limit_l = max_side
        widths = AUTO_WIDTHS
    cache = {}
    best = None
    for w in widths:
        if w > limit_w:
            continue
        for weight, reach in SETTINGS:
            for order in orders:
                pl = _pack(ring, order, w, gap, weight, reach, cache)
                if pl is None:
                    continue
                polys = [Polygon(ring * [sx, sy] + [dx, dy]) for sx, sy, dx, dy in pl]
                x0 = min(p.bounds[0] for p in polys); y0 = min(p.bounds[1] for p in polys)
                x1 = max(p.bounds[2] for p in polys); y1 = max(p.bounds[3] for p in polys)
                size = (x1 - x0, y1 - y0)
                if size[0] > limit_w + 1e-6 or size[1] > limit_l + 1e-6:
                    continue
                if best is None or size[0] * size[1] < best["size"][0] * best["size"][1] - 1e-6:
                    best = dict(placements=[(sx, sy, dx - x0, dy - y0) for sx, sy, dx, dy in pl], size=size)
    if best is None:
        raise ValueError("The pieces don't fit on that bed. Try a bigger one, or leave the size blank.")
    polys = [Polygon(ring * [sx, sy] + [dx, dy]) for sx, sy, dx, dy in best["placements"]]
    best["fill"] = n * area / (best["size"][0] * best["size"][1])
    best["min_gap"] = min(a.distance(b) for i, a in enumerate(polys) for b in polys[i + 1:])
    return best
