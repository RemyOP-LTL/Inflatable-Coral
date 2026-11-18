"""Flat sewing pattern for the sea anemone polyp.

What it makes (all lengths in millimetres):
  1. TUBE   one piece of woven nylon with ONE straight seam down its side. The tube is a smooth shape: wider at the
            bottom, narrower in the middle, wider again at the top (three diameters you choose). Because the shape
            curves, the two flat side edges are curved too, so they get V notches in the seam allowance (as does the top edge; the bottom edge has no allowance).
  2. CAP    a flat disk that closes the top of the tube.
  3. FRILL  ONE long straight strip sewn into the ring seam between the tube top and the cap. Its sewn edge gets V notches
            so the straight strip can bend into a circle. The part that stands out is slit into FRINGE_WIDTH strands
            (non-stretch fabric would scrunch otherwise). Optional solid band between the sew line and the fringe.
Alignment tabs: numbered squares along the side seam (both edges), lettered squares round the ring seam (tube top,
cap and frill). Tack matching tabs together, then sew.

Outputs, in the folder given with --out:
  <name>-detailed.pdf/.svg/.dxf   every line, tab labels included, true size in mm
  <name>-outline.pdf/.svg/.dxf    only the cut lines for the laser (the frill is one closed loop that doubles back along each slit)
  preview-detailed.svg, preview-outline.svg (dark-background previews for the app) and picture-3d.png (the inflated picture)
  <name>.txt      the numbers and the checks

Run:  python3 sea_anemone.py --out some-folder
Change a setting without editing the file:   ANEMONE="HEIGHT=300,DIAMETER_TOP=170" python3 sea_anemone.py ...

How the flat tube is found (plain language)
  The tube is a surface of revolution with a smooth profile (a curve through the three diameters). Such a surface does not
  unroll perfectly flat (an hourglass has to be stretched somewhere). We unroll it like this: the line straight opposite
  the seam stays straight and keeps its length; every ring around the tube becomes an arc of the right length (a full
  circumference) centred on that line. Each arc is bent by a fraction of the way the tube really widens or narrows, and that
  fraction is chosen so the two side edges come out exactly as long as the line opposite them. Where the tube is a plain cone
  this is exact. The in-between lines carry the unavoidable distortion; the report says how large.
"""
import argparse
import math
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

# ----------------------------------------------------------------------------- settings (millimetres)
HEIGHT = 250.0              # height of the tube (bottom opening to the cap), measured straight up the axis
DIAMETER_BOTTOM = 150.0     # ASSUMED. Slightly flared base
DIAMETER_MIDDLE = 130.0     # narrowest part (halfway up). Larger than the ends = a bulge instead
DIAMETER_TOP = 150.0        # ASSUMED. Slightly flared top. The cap disk and the frill ring match this
FRILL_STRIP_LENGTH = 0.0    # length of the frill strip round the ring. 0 = exactly the top circumference (pi x top diameter). More = it gathers
FRILL_LENGTH = 48.0         # ASSUMED. How far the frill stands out (the fringe). The strip's cut width is this + seam allowance + solid band
FRINGE_WIDTH = 6.0          # the standing-out part of the frill is slit into strands this wide
FRILL_WAVE = 3.0            # ASSUMED. How wavy the fringe strands are: height of the wave in mm (0 = straight). All strands wave the same way, so they still nest
FRILL_WAVE_LENGTH = 40.0    # ASSUMED. Length of one wave along a strand
FRILL_BAND = 0.0            # solid (unslit) band between the sew line and the fringe. 0 = fringe starts at the sew line
FRILL_NOTCH_DEPTH = 9.0     # ASSUMED (Remy: 3/8 in = 9.5 mm leaving 3 mm). V notches in the frill's seam allowance (0 = none)
FRILL_NOTCHES_BETWEEN_TABS = 7.0  # ASSUMED. How many notches go between each pair of neighbouring ring tabs on the frill (0 = none). Their width is worked out from the circle
SEAM = 12.0                 # seam allowance on every edge
TUBE_NOTCH_DEPTH = 6.0      # Remy: about 6 mm. V notches in the allowance of the tube: both side edges, the top edge and the bottom edge (0 = none)
TUBE_NOTCHES_BETWEEN_TABS = 3.0   # ASSUMED. How many notches go between each pair of neighbouring tabs along those edges (the bottom edge has no tabs; it uses the same positions as the top)
FABRIC_WIDTH = 1470.0       # ASSUMED usable fabric width (about 58 in), for the fit check
TAB_SIZE = 12.0             # alignment tabs are this-size squares
TAB_SPACING = 125.0         # about one tab every this many mm of seam

NAMES = ["HEIGHT", "DIAMETER_BOTTOM", "DIAMETER_MIDDLE", "DIAMETER_TOP", "FRILL_STRIP_LENGTH", "FRILL_LENGTH", "FRINGE_WIDTH",
         "FRILL_WAVE", "FRILL_WAVE_LENGTH", "FRILL_BAND", "FRILL_NOTCH_DEPTH", "FRILL_NOTCHES_BETWEEN_TABS", "SEAM", "TUBE_NOTCH_DEPTH", "TUBE_NOTCHES_BETWEEN_TABS",
         "FABRIC_WIDTH", "TAB_SIZE", "TAB_SPACING"]


def settings():
    g = globals()
    return {n: g[n] for n in NAMES}


def apply_overrides(text):
    """Read 'NAME=value,NAME=value' (the ANEMONE environment variable) and change those settings."""
    for part in filter(None, (text or "").split(",")):
        k, v = part.split("=")
        k = k.strip().upper()
        if k not in NAMES:
            raise SystemExit(f"Unknown setting {k}. Known: {', '.join(NAMES)}")
        globals()[k] = float(v)


def cumtrapz(y, x):
    return np.concatenate([[0.0], np.cumsum((y[1:] + y[:-1]) / 2 * np.diff(x))])


def unit(v):
    return v / (np.hypot(*v) or 1.0)


# ----------------------------------------------------------------------------- the tube
class Tube:
    def __init__(self, n=3000):
        rb, rm, rt = DIAMETER_BOTTOM / 2, DIAMETER_MIDDLE / 2, DIAMETER_TOP / 2
        if HEIGHT <= 20:
            raise SystemExit("The height must be more than 20 mm.")
        if min(rb, rm, rt) < 10:
            raise SystemExit("Every diameter must be at least 20 mm.")
        H = HEIGHT
        a = 2 * (rb + rt - 2 * rm) / H ** 2                 # profile r(z) = rb + b z + a z^2 through the three diameters
        b = (rt - rb) / H - a * H
        self.z = np.linspace(0, H, n)
        self.r = rb + b * self.z + a * self.z ** 2
        if self.r.min() < 10:
            raise SystemExit("With these three diameters the profile gets too narrow between them. Make the middle wider.")
        rz = b + 2 * a * self.z
        ds = np.sqrt(1 + rz ** 2)
        self.s = cumtrapz(ds, self.z)                      # arclength up the profile
        self.S = float(self.s[-1])
        self.kappa = (rz / ds) / self.r                    # curvature of each ring's arc on the flat: (dr/ds) / r
        self.rb, self.rt = rb, rt
        self.slope_max = float(np.abs(rz / ds).max())
        # An hourglass-type surface cannot unroll perfectly flat. We bend each ring's arc by a fraction `lam` of its
        # true curvature (0 = straight rings, 1 = true curvature) and pick lam so the side edge comes out exactly as
        # long as the line straight opposite the seam. Both seam edges are then the true length; the distortion is
        # pushed to the in-between lines, where fabric can ease it.
        self.lam = 1.0
        grid = np.linspace(0.0, 1.0, 41)
        f = [self.edge_length(l) - self.S for l in grid]
        self.lam = float(grid[int(np.argmin(np.abs(f)))])           # best fraction if the edge can never match exactly (a bulge)
        for i in range(len(grid) - 1):
            if f[i] > 0 >= f[i + 1]:                                  # the edge crosses the right length here: find it precisely
                lo, hi = grid[i], grid[i + 1]
                for _ in range(40):
                    mid = (lo + hi) / 2
                    if self.edge_length(mid) - self.S > 0:
                        lo = mid
                    else:
                        hi = mid
                self.lam = float((lo + hi) / 2)
                break

    def edge_length(self, lam, n=700):
        old = getattr(self, "lam", 1.0)
        self.lam = lam
        _, E = self.edge(-1, n)
        self.lam = old
        return float(np.hypot(*np.diff(E, axis=0).T).sum())

    def radius_s(self, s):
        return np.interp(s, self.s, self.r)

    def pt(self, s, u):
        """Flat position (x across, y down) of the point at profile distance s and sideways arclength u from the
        straight middle line. y = S - X so the top of the tube is at the top of the page."""
        s = np.asarray(s, dtype=float)
        u = np.asarray(u, dtype=float)
        s, u = np.broadcast_arrays(s, u)
        k = self.lam * np.interp(s, self.s, self.kappa)
        phi = k * u
        small = np.abs(phi) < 1e-7
        ks = np.where(small, 1.0, k)
        X = np.where(small, s, s - (1 - np.cos(phi)) / ks)
        Y = np.where(small, u, np.sin(phi) / ks)
        return np.column_stack([Y, self.S - X])

    def edge(self, side, n=700):
        s = np.linspace(0, self.S, n)
        return s, self.pt(s, side * math.pi * self.radius_s(s))

    def arc(self, s0, n=240):
        r = float(self.radius_s(s0))
        u = np.linspace(-math.pi * r, math.pi * r, n)
        return u, self.pt(np.full_like(u, s0), u)

    def outline(self):
        _, L = self.edge(-1)
        _, R = self.edge(+1)
        _, T = self.arc(self.S)
        _, B = self.arc(0.0)
        return np.vstack([L, T, R[::-1], B[::-1]])

    def edge_frame(self, s, side):
        d = 0.5
        pts = [self.pt(min(max(s + e, 0), self.S), side * math.pi * float(self.radius_s(min(max(s + e, 0), self.S))))[0] for e in (-d, d)]
        return (pts[0] + pts[1]) / 2, unit(pts[1] - pts[0])

    def ring_frame(self, s0, u):
        d = 0.5
        pts = [self.pt(s0, u + e)[0] for e in (-d, d)]
        return (pts[0] + pts[1]) / 2, unit(pts[1] - pts[0])


def tab_square(p, t, n, off, size):
    """A square tab on the side n of the edge point p (tangent t), starting `off` from the edge."""
    a, b = off - 5, off + size
    h = size / 2
    return Polygon([p + t * -h + n * a, p + t * h + n * a, p + t * h + n * b, p + t * -h + n * b])


def outward(p, t, poly):
    n = np.array([-t[1], t[0]])
    return -n if poly.contains(Point(p + n * 0.8)) else n


def tab_positions(lo, hi, spacing):
    """Tab centres between lo and hi: both ends and about one every `spacing`."""
    if hi <= lo:
        return [(lo + hi) / 2]
    k = max(1, math.ceil((hi - lo) / spacing))
    return list(np.linspace(lo, hi, k + 1))


def ring_notch_fracs(tab_f, n):
    """Notch positions round a closed ring (as fractions 0..1): n evenly spaced notches between each pair of neighbouring
    tabs. The tabs are evenly spaced, so this is one even spacing all the way round with a tab in every (n+1)th place."""
    m = len(tab_f)
    return sorted((f + k / (m * (n + 1))) % 1.0 for f in tab_f for k in range(1, n + 1))


def v_notch(p, t, n, depth, half_w, out=2.0):
    """A V cut into the seam allowance: tip `depth` in from the cut edge, opening beyond it. p = point on the sew line,
    n = outward direction, t = along the edge."""
    return Polygon([p + n * (SEAM - depth), p + n * (SEAM + out) - t * half_w * (depth + out) / depth,
                    p + n * (SEAM + out) + t * half_w * (depth + out) / depth])


class Piece:
    def __init__(self, name):
        self.name, self.items = name, []

    def add(self, kind, pts, text=None):
        self.items.append((kind, np.asarray(pts, float), text))


# ----------------------------------------------------------------------------- build
def build():
    T = Tube()
    warn = []
    outline = Polygon(T.outline()).buffer(0)
    body = outline.buffer(SEAM, join_style=2, mitre_limit=4)
    # no seam allowance on the bottom edge of the tube (Remy): keep only what lies above the bottom edge
    Bp = T.arc(0.0)[1]
    tL, tR = unit(Bp[1] - Bp[0]), unit(Bp[-1] - Bp[-2])
    keep = [tuple(Bp[0] - tL * 40)] + [tuple(q) for q in Bp] + [tuple(Bp[-1] + tR * 40)]
    bx0, bx1 = body.bounds[0] - 50, body.bounds[2] + 50                 # wide enough for a bulging tube
    keep += [(bx1, keep[-1][1]), (bx1, keep[-1][1] - 3000), (bx0, keep[0][1] - 3000), (bx0, keep[0][1])]
    body = body.intersection(Polygon(keep))
    h = TAB_SIZE / 2
    R_top = DIAMETER_TOP / 2
    circ_top = 2 * math.pi * R_top
    n_ring = max(2, round(circ_top / TAB_SPACING))
    ring_f = [(i + 0.5) / n_ring for i in range(n_ring)]                 # tab positions round the ring, as fractions
    ring_lab = [chr(ord("A") + i) for i in range(n_ring)]
    # --- tube: tabs along both side edges, ring tabs along the top edge
    squares, labels = [], []
    side_s = tab_positions(2 * TAB_SIZE, T.S - 2 * TAB_SIZE, TAB_SPACING)
    for i, s in enumerate(side_s, start=1):
        for side in (-1, 1):
            p, t = T.edge_frame(s, side)
            n = outward(p, t, outline)
            squares.append(tab_square(p, t, n, SEAM, TAB_SIZE))
            labels.append((p + n * (SEAM + h), str(i)))
    for f, lab in zip(ring_f, ring_lab):
        u = -math.pi * T.rt + f * circ_top
        p, t = T.ring_frame(T.S, u)
        n = outward(p, t, outline)
        squares.append(tab_square(p, t, n, SEAM, TAB_SIZE))
        labels.append((p + n * (SEAM + h), lab))
    cut = unary_union([body] + squares)
    # --- notches in the allowance, n between each pair of tabs: both side edges and the top edge (no allowance on the bottom edge)
    n_tube_notches = n_skipped = 0
    depth = min(TUBE_NOTCH_DEPTH, SEAM - 2.0)
    n_between = int(round(TUBE_NOTCHES_BETWEEN_TABS))
    if depth > 0.5 and n_between > 0:
        tabs_union = unary_union(squares)
        half_w = depth * math.tan(math.radians(25))                       # a 50 degree V
        cutters = []

        def add_notch(p, t):
            nonlocal n_tube_notches, n_skipped
            n = outward(p, t, outline)
            c = v_notch(p, t, n, depth, half_w)
            if c.distance(tabs_union) < 1.5:                               # would run into a tab
                n_skipped += 1
                return
            cutters.append(c)
            n_tube_notches += 1
        for a_, b_ in zip(side_s[:-1], side_s[1:]):                       # side edges: between each pair of numbered tabs
            for k in range(1, n_between + 1):
                sn = a_ + (b_ - a_) * k / (n_between + 1)
                for side in (-1, 1):
                    add_notch(*T.edge_frame(sn, side))
        for f in ring_notch_fracs(ring_f, n_between):                     # top edge, between the lettered tabs
            if min(f, 1 - f) * 2 * math.pi * T.rt < 1.5 * SEAM:           # not in the corner where the side seam joins
                continue
            add_notch(*T.ring_frame(T.S, -math.pi * T.rt + f * 2 * math.pi * T.rt))
        if cutters:
            cut = cut.difference(unary_union(cutters))
        if n_skipped:
            warn.append(f"{n_skipped} tube notch(es) were left out because they would run into a tab. Use fewer notches between tabs.")
    if cut.geom_type != "Polygon" or len(cut.interiors) > 0:
        warn.append("The tube's cut outline touches itself. Make the seam allowance smaller or move the notches apart.")
        if cut.geom_type != "Polygon":
            cut = max(cut.geoms, key=lambda g: g.area)
    tube = Piece("tube")
    tube.add("cut", np.array(cut.exterior.coords))
    tube.add("sew", np.array(outline.exterior.coords))
    for p, txt in labels:
        tube.add("label", [p], txt)
    pieces = [tube]
    # --- cap disk
    ccx = ccy = R_top + SEAM
    csq, clab = [], []
    for f, lab in zip(ring_f, ring_lab):
        a = f * 2 * math.pi
        n = np.array([math.cos(a), math.sin(a)])
        p = np.array([ccx, ccy]) + n * R_top
        t = np.array([-n[1], n[0]])
        csq.append(tab_square(p, t, n, SEAM, TAB_SIZE))
        clab.append((p + n * (SEAM + h), lab))
    ccut = unary_union([Point(ccx, ccy).buffer(R_top + SEAM, 180)] + csq)
    cap = Piece("cap")
    cap.add("cut", np.array(ccut.exterior.coords))
    cap.add("sew", np.array(Point(ccx, ccy).buffer(R_top, 180).exterior.coords))
    for p, txt in clab:
        cap.add("label", [p], txt)
    pieces.append(cap)
    # --- frill: one straight strip. y = 0 is the cut edge of the seam allowance, y = SEAM the sew line
    Lf = FRILL_STRIP_LENGTH if FRILL_STRIP_LENGTH > 0 else circ_top
    y_fringe = SEAM + FRILL_BAND                           # fringe (slits) starts here
    W = y_fringe + FRILL_LENGTH                            # cut width of the strip: allowance + band + how far the fringe stands out
    if W - y_fringe < FRINGE_WIDTH:
        raise SystemExit(f"The frill length must be at least {FRINGE_WIDTH:g} mm (one strand wide).")
    if FRINGE_WIDTH < 1:
        raise SystemExit("Fringe strand width must be at least 1 mm.")
    n_slits = max(1, round(Lf / FRINGE_WIDTH))
    strand = Lf / n_slits
    rect = Polygon([[0, 0], [Lf, 0], [Lf, y_fringe], [0, y_fringe]])      # the solid part (allowance + band); the fringe is added below
    ftabs, flabs, tab_x = [], [], []
    for f, lab in zip(ring_f, ring_lab):
        x = f * Lf
        tab_x.append(x)
        ftabs.append(tab_square(np.array([x, 0.0]), np.array([1.0, 0.0]), np.array([0.0, -1.0]), 0.0, TAB_SIZE))
        flabs.append((np.array([x, -h]), lab))
    fcut = unary_union([rect] + ftabs)
    n_fn = 0
    fdepth = min(FRILL_NOTCH_DEPTH, SEAM - 1.5)
    notch_w = 0.0
    f_between = int(round(FRILL_NOTCHES_BETWEEN_TABS))
    if fdepth > 0.5 and f_between > 0:
        sp = Lf / (len(ring_f) * (f_between + 1))                     # distance between neighbouring notches
        fracs = [f for f in ring_notch_fracs(ring_f, f_between) if min(f, 1 - f) * Lf > 1.5 * SEAM]   # none in the corner where the strip's ends meet
        notch_w = min(2 * math.pi * SEAM / max(len(fracs), 1), 0.8 * sp)   # together they take out the allowance's extra length (2 pi x allowance)
        fcutters = []
        for f in fracs:
            x = f * Lf
            if True:
                fcutters.append(Polygon([(x, fdepth), (x - notch_w / 2 * (fdepth + 2) / fdepth, -2),
                                         (x + notch_w / 2 * (fdepth + 2) / fdepth, -2)]))
                n_fn += 1
        if fcutters:
            fcut = fcut.difference(unary_union(fcutters))
    shift = np.array([0.0, TAB_SIZE])                      # tabs hang above the strip's allowance edge, so lift everything
    pts = [tuple(q) for q in fcut.exterior.coords][:-1]
    i0 = min(range(len(pts)), key=lambda i: abs(pts[i][0]) + abs(pts[i][1] - y_fringe))
    pts = pts[i0:] + pts[:i0]
    if abs(pts[1][1] - y_fringe) < 1e-9 and pts[1][0] > 1:                 # ring runs along the bottom first: turn it round
        pts = [pts[0]] + pts[:0:-1]
    top_path = [list(q) for q in pts]                      # from (0, y_fringe) up round the allowance edge to (Lf, y_fringe)
    # fringe: wavy strands with round ends. Every slit is the same wave shifted along, so the strands nest exactly.
    r_end = strand / 2
    y_e = W - r_end                                        # where the straight-sided part of each strand ends and its round tip starts
    fl = y_e - y_fringe
    if fl < 2:
        raise SystemExit("The fringe is too short for its round ends: make the frill wider or the strands narrower.")
    ramp = min(10.0, 0.35 * fl)                            # the wave eases in and out so the tips are straight and the cap is clean
    ys = np.linspace(y_fringe, y_e, max(24, math.ceil(fl / 1.5)))

    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)
    wave = FRILL_WAVE * smooth((ys - y_fringe) / ramp) * smooth((y_e - ys) / ramp) * np.sin(2 * math.pi * (ys - y_fringe) / max(FRILL_WAVE_LENGTH, 5.0))

    def curve(k):
        return np.column_stack([k * strand + wave, ys])
    loop = list(top_path) + curve(n_slits).tolist()        # ONE closed loop: down the right end, then along the free edge
    ang = np.linspace(0, math.pi, 28)
    for j in range(n_slits - 1, -1, -1):
        cx = (j + 0.5) * strand
        loop += [[cx + r_end * math.cos(a_), y_e + r_end * math.sin(a_)] for a_ in ang]       # round tip of strand j
        c = curve(j)
        loop += (c[::-1].tolist() + c.tolist()) if j > 0 else c[::-1].tolist()                  # each slit up and back down (doubled); the left end only up
    clean = [loop[0]]
    for q in loop[1:]:
        if math.hypot(q[0] - clean[-1][0], q[1] - clean[-1][1]) > 1e-9:
            clean.append(q)
    if math.hypot(clean[-1][0] - clean[0][0], clean[-1][1] - clean[0][1]) > 1e-9:
        clean.append(clean[0])
    loop = clean
    frill = Piece("frill")
    frill.add("cut", np.array(loop) + shift)
    frill.add("sew", np.array([[0, SEAM], [Lf, SEAM]]) + shift)
    if FRILL_BAND > 0:
        frill.add("mark", np.array([[0, y_fringe], [Lf, y_fringe]]) + shift)
    for p, txt in flabs:
        frill.add("label", [p + shift], txt)
    pieces.append(frill)
    # --- numbers and checks
    xs, ys = np.array(outline.minimum_rotated_rectangle.exterior.coords).T
    sides = sorted([math.hypot(xs[1] - xs[0], ys[1] - ys[0]), math.hypot(xs[2] - xs[1], ys[2] - ys[1])])
    cb = cut.bounds
    _, Ledge = T.edge(-1)
    edge_len = float(np.hypot(*np.diff(Ledge, axis=0).T).sum())
    if sides[0] + 2 * SEAM > FABRIC_WIDTH:
        warn.append(f"The tube is {sides[0] + 2 * SEAM:.0f} mm across (tightest fit) and does not fit the {FABRIC_WIDTH:.0f} mm fabric.")
    if abs(Lf - circ_top) / circ_top > 0.02:
        pct = (Lf / circ_top - 1) * 100
        warn.append(f"The frill is {abs(pct):.0f}% {'longer' if pct > 0 else 'shorter'} than the ring it goes round "
                    f"({circ_top:.0f} mm). " + ("It will gather a little." if pct > 0 else "It will leave a gap."))
    if FRILL_NOTCH_DEPTH > SEAM - 1.5 and FRILL_NOTCH_DEPTH > 0:
        warn.append(f"Frill notch depth was cut back to {fdepth:g} mm so at least 1.5 mm of the allowance stays solid.")
    if abs(edge_len / T.S - 1) > 0.05:
        warn.append(f"The flat side edge is {edge_len:.0f} mm but the tube is {T.S:.0f} mm tall along its surface "
                    f"({(edge_len / T.S - 1) * 100:+.0f}%). The shape is quite curved, so expect to ease the seam while sewing.")
    d_mid = DIAMETER_MIDDLE
    info = dict(pieces=len(pieces), tube_s=T.S, edge_len=edge_len, tube_tight=sides[0] + 2 * SEAM, tube_long=sides[1] + 2 * SEAM,
                bbox=(cb[2] - cb[0], cb[3] - cb[1]), circ_top=circ_top, circ_bottom=math.pi * DIAMETER_BOTTOM,
                circ_mid=math.pi * d_mid, frill_len=Lf, frill_w=W, F=W - y_fringe, n_slits=n_slits, strand=strand,
                n_tube_notches=n_tube_notches, n_frill_notches=n_fn, notch_w=notch_w, side_tabs=len(side_s), ring_tabs=n_ring,
                cap_d=2 * (R_top + SEAM), slope_max=T.slope_max, warnings=warn)
    return T, outline, cut, pieces, info


def report(info):
    L = ["SEA ANEMONE POLYP: flat pattern numbers (millimetres)", "", "Settings:"]
    L += [f"  {k:<20} {v:g}" for k, v in settings().items()]
    L += ["", "Results:",
          f"  Tube                            {HEIGHT:g} mm tall (surface line {info['tube_s']:.0f} mm), {DIAMETER_BOTTOM:g} mm across at the bottom, "
          f"{DIAMETER_MIDDLE:g} mm in the middle, {DIAMETER_TOP:g} mm at the top",
          f"  Tube piece, cut size            bounding box {info['bbox'][0]:.0f} x {info['bbox'][1]:.0f} mm, "
          f"tightest rectangle {info['tube_tight']:.0f} x {info['tube_long']:.0f} mm",
          f"  Straight seam                   one side seam, flat edge {info['edge_len']:.0f} mm long (surface line {info['tube_s']:.0f} mm)",
          f"  Circumference                   bottom {info['circ_bottom']:.0f}, middle {info['circ_mid']:.0f}, top {info['circ_top']:.0f} mm",
          f"  Cap disk                        {info['cap_d']:.0f} mm across with allowance ({DIAMETER_TOP:g} mm sew circle)",
          f"  Frill                           one strip {info['frill_len']:.0f} x {info['frill_w']:.0f} mm; {SEAM:g} mm seam allowance"
          + (f", {FRILL_BAND:g} mm solid band" if FRILL_BAND > 0 else "")
          + f", {info['F']:.0f} mm of fringe slit into {info['n_slits']} strands {info['strand']:.1f} mm wide",
          (f"  Frill seam notches              {info['n_frill_notches']} V notches, {FRILL_NOTCHES_BETWEEN_TABS:g} between each pair of tabs, {min(FRILL_NOTCH_DEPTH, SEAM - 1.5):g} mm deep, "
           f"{info['notch_w']:.1f} mm wide at the cut edge (width worked out from the circle)") if info["n_frill_notches"]
          else "  Frill seam notches              none",
          (f"  Tube seam notches               {info['n_tube_notches']} V notches, {TUBE_NOTCHES_BETWEEN_TABS:g} between each pair of tabs, {min(TUBE_NOTCH_DEPTH, SEAM - 2.0):g} mm deep, "
           f"on both side edges and the top edge (none on the bottom edge, which has no allowance, or on the cap)") if info["n_tube_notches"] else "  Tube seam notches               none",
          f"  Alignment tabs                  {TAB_SIZE:g} mm squares: {info['side_tabs']} numbered pairs on the side seam, "
          f"{info['ring_tabs']} lettered sets (tube top, cap, frill) round the ring",
          f"  Pieces to cut                   {info['pieces']}", ""]
    L += ["Checks:"] + (["  " + w for w in info["warnings"]] or ["  none"])
    return "\n".join(L)


# ----------------------------------------------------------------------------- layout and drawing
def piece_box(p):
    a = np.vstack([a for k, a, t in p.items if k == "cut"])
    return a.min(axis=0), a.max(axis=0)


def layout(pieces):
    """Offsets (dx, dy) of each piece, and the title position, packed in rows. Returns {name: (dx, dy, tx, ty)}."""
    gap, title_h = 30.0, 22.0
    boxes = [piece_box(p) for p in pieces]
    sizes = [b[1] - b[0] for b in boxes]
    limit = max(sizes[0][0], sum(s[0] for s in sizes[1:]) + gap * (len(sizes) - 2))
    place = {}
    x, y, rowh = 0.0, title_h, 0.0
    for p, (lo, hi), sz in zip(pieces, boxes, sizes):
        if x > 0 and x + sz[0] > limit + 1e-6:
            x, y, rowh = 0.0, y + rowh + gap + title_h, 0.0
        place[p.name] = (x - lo[0], y - lo[1], x, y - 6)
        x += sz[0] + gap
        rowh = max(rowh, sz[1])
    return place


def title(name):
    return {"tube": "TUBE (cut 1). One straight seam: sew the two side edges together",
            "cap": "CAP DISK (cut 1)",
            "frill": "FRILL STRIP (cut 1). Sew along the blue line; the slits make the fringe"}[name]


def export_items(pieces, detailed):
    """Everything an export file draws, at true size in mm, y pointing down, shifted so the drawing starts 10 mm in from
    the corner. detailed=False keeps only the cut lines (what the laser follows): one closed outline per piece.
    Returns (items, width, height); items are (kind, points, text) with kind cut / sew / mark / label / title."""
    place = layout(pieces)
    items = []
    for p in pieces:
        dx, dy, tx, ty = place[p.name]
        for k, a, t in p.items:
            if k != "cut" and not detailed:
                continue
            items.append((k, a + np.array([dx, dy]), t))
        if detailed:
            items.append(("title", np.array([[tx, ty]]), title(p.name)))
    allp = np.vstack([a for k, a, t in items])
    lo = allp.min(axis=0) - 10.0
    hi = allp.max(axis=0) + 10.0
    if detailed:
        hi[0] = max(hi[0], lo[0] + 90.0)
    items = [(k, a - lo, t) for k, a, t in items]
    return items, float(hi[0] - lo[0]), float(hi[1] - lo[1])


def write_svg(path, pieces, detailed):
    items, w, h = export_items(pieces, detailed)
    style = {"cut": 'stroke="#d00000" stroke-width="0.5" fill="none"',
             "sew": 'stroke="#1d4ed8" stroke-width="0.4" stroke-dasharray="3 2" fill="none"',
             "mark": 'stroke="#777" stroke-width="0.4" stroke-dasharray="1.2 3" fill="none"'}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.3f} {h:.3f}">',
           "<!-- Units are millimetres, true size. " + ("Red = cut, blue dashed = sew line, grey dotted = solid band edge. Squares are alignment tabs. -->"
                                                       if detailed else "Only the cut lines. -->")]
    for k, a, t in items:
        if k == "label":
            out.append(f'<text x="{a[0][0]:.2f}" y="{a[0][1] + 1.8:.2f}" font-size="5" text-anchor="middle" font-family="sans-serif" fill="#d00000">{t}</text>')
        elif k == "title":
            out.append(f'<text x="{a[0][0]:.2f}" y="{a[0][1]:.2f}" font-size="9" font-family="sans-serif" fill="#555">{t}</text>')
        else:
            out.append(f'<polyline points="{" ".join(f"{x:.3f},{y:.3f}" for x, y in a)}" {style[k]}/>')
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))


def write_pdf(path, pieces, detailed):
    """True-size PDF: the page is exactly as big as the drawing (1 PDF point = 1/72 inch), no grid, no scales.
    Laser version: black 0.001 in lines, nothing else."""
    items, w, h = export_items(pieces, detailed)
    fig = plt.figure(figsize=(w / 25.4, h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.axis("off")
    fig.patch.set_visible(False)                      # no white background rectangle for the laser software to pick up
    sty = {"cut": ("#d00000", "-", 0.5) if detailed else ("#000000", "-", 0.001 * 72), "sew": ("#1d4ed8", (0, (4, 3)), 0.4), "mark": ("#777777", ":", 0.4)}
    for k, a, t in items:
        if k == "label":
            ax.text(a[0][0], a[0][1], t, fontsize=5, ha="center", va="center", color="#d00000")
        elif k == "title":
            ax.text(a[0][0], a[0][1], t, fontsize=7, ha="left", va="baseline", color="#555555")
        else:
            c_, ls, lw = sty[k]
            ax.plot(a[:, 0], a[:, 1], color=c_, ls=ls, lw=lw, solid_capstyle="butt")
    fig.savefig(path, format="pdf")
    plt.close(fig)


def write_dxf(path, pieces, detailed):
    """Laser/CAD file, true size, units = millimetres. Plain ASCII DXF (R12 style), no extra libraries.
    Layer CUT (one closed outline per piece); detailed adds SEW, MARK, LABELS, TITLES. The y axis points up."""
    items, w, h = export_items(pieces, detailed)
    code = []

    def put(c, v):
        code.append(f"{c}\n{v}")

    ents = []
    for k, a, t in items:
        if k == "label" or k == "title":
            ents.append(("LABELS" if k == "label" else "TITLES", "text", a[0], t))
            continue
        closed = len(a) > 3 and np.allclose(a[0], a[-1])
        layer = {"cut": "CUT", "sew": "SEW", "mark": "MARK"}[k]
        ents.append((layer, "poly", a[:-1] if closed else a, closed))
    put(0, "SECTION"); put(2, "HEADER")
    put(9, "$ACADVER"); put(1, "AC1009")
    put(9, "$INSUNITS"); put(70, 4)                                     # 4 = millimetres
    put(9, "$MEASUREMENT"); put(70, 1)                                  # 1 = metric
    put(9, "$EXTMIN"); put(10, "0.0"); put(20, f"{-h:.4f}"); put(30, 0)
    put(9, "$EXTMAX"); put(10, f"{w:.4f}"); put(20, "0.0"); put(30, 0)
    put(0, "ENDSEC")
    layers = {"CUT": 1, "SEW": 5, "MARK": 8, "LABELS": 1, "TITLES": 8}
    put(0, "SECTION"); put(2, "TABLES"); put(0, "TABLE"); put(2, "LAYER"); put(70, len(layers))
    for nm, col in layers.items():
        put(0, "LAYER"); put(2, nm); put(70, 0); put(62, col); put(6, "CONTINUOUS")
    put(0, "ENDTAB"); put(0, "ENDSEC")
    put(0, "SECTION"); put(2, "ENTITIES")
    for layer, kind, g, extra in ents:
        if kind == "text":
            put(0, "TEXT"); put(8, layer); put(10, f"{g[0]:.4f}"); put(20, f"{-g[1]:.4f}"); put(30, 0)
            put(40, 5 if layer == "LABELS" else 9); put(1, extra)
            if layer == "LABELS":
                put(72, 1); put(11, f"{g[0]:.4f}"); put(21, f"{-g[1]:.4f}"); put(31, 0)
        else:
            put(0, "POLYLINE"); put(8, layer); put(66, 1); put(70, 1 if extra else 0)
            for x, y in g:
                put(0, "VERTEX"); put(8, layer); put(10, f"{x:.4f}"); put(20, f"{-y:.4f}"); put(30, 0)
            put(0, "SEQEND"); put(8, layer)
    put(0, "ENDSEC"); put(0, "EOF")
    with open(path, "w") as f:
        f.write("\n".join(code) + "\n")


BG = "#1c1b1a"            # the dark background of the previews in the app (exports for the laser are not affected)


def _axes(ax):
    ax.set_aspect("equal")
    ax.grid(alpha=.12, color="#ffffff")
    ax.set_xlabel("mm", color="#bbbbbb"); ax.set_ylabel("mm", color="#bbbbbb")
    sx = ax.secondary_xaxis("top", functions=(lambda v: v / 25.4, lambda v: v * 25.4)); sx.set_xlabel("inches", color="#bbbbbb")
    sy = ax.secondary_yaxis("right", functions=(lambda v: v / 25.4, lambda v: v * 25.4)); sy.set_ylabel("inches", color="#bbbbbb")
    for a in (ax, sx, sy):
        a.tick_params(colors="#aaaaaa")
    for sp in ax.spines.values():
        sp.set_color("#555555")


def draw_preview(path, pieces, detailed):
    """The flat-pattern preview for the app, as a dark-background SVG (vector, so it stays sharp when zoomed). Lines keep a
    constant thickness on screen when zoomed. Detailed = every line and label; laser view = cut lines only."""
    import re
    matplotlib.rcParams["svg.fonttype"] = "none"
    items, w, h = export_items(pieces, detailed)
    fig = plt.figure(figsize=(14, max(4.0, 14 * h / w + 1.3)), facecolor=BG)
    ax = fig.add_subplot(111, facecolor=BG)
    col = {"cut": ("#ff6a5c", "-", 1.2), "sew": ("#6aa7e8", "--", 1.0), "mark": ("#999999", ":", 1.0)}
    for k, a, t in items:
        if k == "label":
            ax.text(a[0][0], a[0][1], t, fontsize=6, ha="center", va="center", color="#ff9a8f")
        elif k == "title":
            ax.text(a[0][0], a[0][1], t, fontsize=8, color="#d0d0d0")
        else:
            ax.plot(a[:, 0], a[:, 1], color=col[k][0], ls=col[k][1], lw=col[k][2])
    ax.set_xlim(0, w); ax.set_ylim(h, 0)
    _axes(ax)
    fig.tight_layout()
    fig.savefig(path, format="svg", facecolor=BG)
    plt.close(fig)
    with open(path) as f:
        svg = f.read()
    svg = re.sub(r'(<path [^>]*?style=")', r'\1vector-effect: non-scaling-stroke; ', svg)
    with open(path, "w") as f:
        f.write(svg)


def draw_picture(path, T, info):
    """The inflated 3D picture (white anemone on the dark background)."""
    fig = plt.figure(figsize=(8, 9.5), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1], facecolor=BG)
    import anemone_3d
    anemone_3d.draw(ax, T, T.S, DIAMETER_TOP / 2, info["F"], info["strand"], info["n_slits"], FRILL_WAVE, FRILL_WAVE_LENGTH)
    fig.savefig(path, dpi=130, facecolor=BG)
    plt.close(fig)


def make(out, name="sea-anemone"):
    os.makedirs(out, exist_ok=True)
    T, outline, cut, pieces, info = build()
    for view, detailed in (("detailed", True), ("outline", False)):     # the two views the page can show, each exported three ways
        for ext, fn in (("svg", write_svg), ("pdf", write_pdf), ("dxf", write_dxf)):
            fn(os.path.join(out, f"{name}-{view}.{ext}"), pieces, detailed)
    draw_preview(os.path.join(out, "preview-detailed.svg"), pieces, True)       # the two zoomable previews and the 3D picture for the app
    draw_preview(os.path.join(out, "preview-outline.svg"), pieces, False)
    draw_picture(os.path.join(out, "picture-3d.png"), T, info)
    text = report(info)
    with open(os.path.join(out, name + ".txt"), "w") as f:
        f.write(text + "\n")
    return info, text


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    ap.add_argument("--name", default="sea-anemone")
    a = ap.parse_args()
    apply_overrides(os.environ.get("ANEMONE"))
    info, text = make(a.out, a.name)
    print(text)


if __name__ == "__main__":
    main()
