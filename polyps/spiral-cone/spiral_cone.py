"""Flat sewing pattern for the spiral-cone polyp.

What it makes (all lengths in millimetres):
  1. CONE STRIP   one long curved strip of woven nylon. Wound in a spiral it becomes the cone, cuff included.
                  The seam winds up the cone (tighter toward the tip), then runs out into a straight seam
                  for the last STRAIGHT_LENGTH mm. The open end of the cuff has no seam allowance.
  2. FRILL        ONE long straight strip sewn into the spiral seam: a solid seam allowance along the sewn edge
                  (12 mm), and the part that stands out on the outside is slit into FRINGE_WIDTH (6 mm) strands,
                  so nothing scrunches when the fabric will not stretch. It starts FRILL_START mm up the cone
                  and ends where the spiral ends.
  3. (optional)   a separate straight cuff band, with CUFF_IN_STRIP = 0.
Alignment tabs: 12 mm squares sticking out of the cut edges at matching places along the seam (both cone
edges and the frill) and along the straight seam. Tack the tabs together, then sew.

Outputs, in the folder given with --out:
  <name>-detailed.pdf/.svg/.dxf   every line, tab numbers included, true size in mm
  <name>-outline.pdf/.svg/.dxf    only the cut lines for the laser (frill = one closed loop doubling back along each slit), true size in mm
  <name>.png (flat pieces + 3D sketch) and <name>-outline.png   the two previews
  <name>.txt      the numbers and the checks

Run:  python3 spiral_cone.py --out some-folder
Change a setting without editing the file:   CONE="LENGTH=300,BASE_DIAMETER=150" python3 spiral_cone.py ...

How the flat shapes are found
  A cone (even a cut-off cone) unrolls flat with no stretching, like a paper party hat. A seam that winds up
  the cone becomes a spiral curve on that flat fan. The seam goes round theta(z) = 2 pi * integral dz / pitch(z);
  over the last TRANSITION mm before the straight seam the winding fades to zero so the seam turns smoothly
  straight. The strip is what lies between one turn of the seam and the next turn above it.
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
LENGTH = 250.0              # cone height above the cuff line (the straight seam part included)
BASE_DIAMETER = 130.0       # measured at the cuff line (the top of the cuff = the tube fit)
TIP_DIAMETER = 0.0          # 0 = the cone comes to a point (Remy, 2026-11-16). The string is anchored at the point.
PITCH_BASE = 75.0           # ASSUMED. Height gained per turn at the bottom of the cone
PITCH_TIP = 50.0            # ASSUMED. Same where the spiral ends (smaller = tighter wind toward the tip)
PITCH_CURVE = 1.0           # 1 = pitch changes evenly with height; >1 stays open longer, then tightens late
STRAIGHT_LENGTH = 50.0      # the last this-many mm of the cone have a straight seam (Remy)
TRANSITION = 50.0           # the spiral fades into the straight seam over this length (0 = sharp corner)
SEAM = 12.0                 # seam allowance (every edge except the open end of the cuff)
NOTCH_DEPTH = 8.0           # ASSUMED. V notches cut into the seam allowance along the curved edges so it lies flat round the curve (0 = none)
NOTCH_SPACING_BASE = 60.0   # ASSUMED. Distance between notches along the seam at the base (cuff) end
NOTCH_SPACING_TIP = 20.0    # ASSUMED. Same at the tip end of the spiral (closer together where the curve is tighter)
RUFFLE_WIDTH = 75.0         # cut width of the frill strip: solid seam allowance + (width - seam) of fringe standing out
FRILL_START = 75.0          # where the frill starts, in mm up the axis from the cuff line (Remy)
FRILL_END_FROM_TIP = 50.0   # where the frill ends: this many mm from the tip, measured along the axis (must be at least STRAIGHT_LENGTH)
CUFF_HEIGHT = 50.0          # finished height of the cuff
CUFF_IN_STRIP = 1           # 1 = cuff is the bottom of the cone strip. 0 = separate straight cuff band
HEM = 25.0                  # only for the separate cuff band: extra at its open end
FABRIC_WIDTH = 1473.2       # ASSUMED usable width of the fabric: 58 in (the one thing Remy buys in inches; the tool shows it in inches)
TAB_SIZE = 12.0             # alignment tabs are this-size squares
TAB_SPACING = 125.0         # about one tab every this many mm of seam
FRINGE_WIDTH = 6.0          # the standing-out part of the frill is slit into strands this wide

NAMES = ["LENGTH", "BASE_DIAMETER", "TIP_DIAMETER", "PITCH_BASE", "PITCH_TIP", "PITCH_CURVE", "STRAIGHT_LENGTH",
         "TRANSITION", "SEAM", "NOTCH_DEPTH", "NOTCH_SPACING_BASE", "NOTCH_SPACING_TIP", "RUFFLE_WIDTH", "FRILL_START", "FRILL_END_FROM_TIP", "CUFF_HEIGHT", "CUFF_IN_STRIP", "HEM",
         "FABRIC_WIDTH", "TAB_SIZE", "TAB_SPACING", "FRINGE_WIDTH"]


def settings():
    g = globals()
    return {n: g[n] for n in NAMES}


def apply_overrides(text):
    """Read 'NAME=value,NAME=value' (the CONE environment variable) and change those settings."""
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


# ----------------------------------------------------------------------------- the cone and its seam
class Cone:
    def __init__(self, n=6000):
        self.L = LENGTH
        self.Ls = LENGTH - STRAIGHT_LENGTH               # where the spiral ends
        self.r0 = BASE_DIAMETER / 2
        self.r1 = TIP_DIAMETER / 2
        if self.r1 < 0 or self.r1 >= self.r0 - 1e-3:
            raise SystemExit("The tip must be narrower than the base (0 <= TIP_DIAMETER < BASE_DIAMETER).")
        if PITCH_TIP <= 0 or PITCH_BASE <= 0:
            raise SystemExit("Pitch must be above zero.")
        if STRAIGHT_LENGTH < 0 or self.Ls <= 12:
            raise SystemExit("The straight part must be shorter than the cone.")
        if not (0 <= FRILL_START < self.Ls - 12):
            raise SystemExit("The frill must start above the cuff line and below the end of the spiral "
                             f"(FRILL_START between 0 and {self.Ls - 12:g}).")
        if FRILL_END_FROM_TIP < STRAIGHT_LENGTH - 1e-6:
            raise SystemExit(f"The frill cannot run into the straight seam: 'Frill ends from tip' must be at least the straight seam length ({STRAIGHT_LENGTH:g} mm).")
        self.z_f1 = LENGTH - FRILL_END_FROM_TIP               # height where the frill ends
        if self.z_f1 - FRILL_START < 12:
            raise SystemExit("The frill is too short: it must start at least 12 mm below where it ends. Lower 'Frill starts at' or 'Frill ends from tip'.")
        self.zmin = -CUFF_HEIGHT if CUFF_IN_STRIP else 0.0
        self.slant = math.hypot(self.L, self.r0 - self.r1)
        self.sing = (self.r0 - self.r1) / self.slant       # sin of the cone's half angle
        self.cosg = math.sqrt(1 - self.sing ** 2)
        self.rho0 = self.r0 / self.sing                    # flat distance apex -> cuff line
        self.rho_bottom = self.rho0 - self.zmin * self.slant / self.L
        # seam: theta(z) from winding rate w(z) = fade(z) / pitch(z); dtheta/dz = 2 pi w
        self.zg = np.linspace(self.zmin, self.Ls, n)
        self.w = self._fade(self.zg) / self.pitch(self.zg)
        self.thg = 2 * math.pi * cumtrapz(self.w, self.zg)
        self.theta_end = float(self.thg[-1])
        self.theta_c = self.theta_end - 2 * math.pi
        if self.theta_c < -1e-6:
            raise SystemExit("The seam makes less than one full turn. Make the pitch smaller or the cone longer.")
        self.theta_z0 = float(np.interp(0.0, self.zg, self.thg))
        P = self.flat(self.thg, self.zg)
        self.s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
        self.s_f0 = float(np.interp(FRILL_START, self.zg, self.s))
        self.s_total = float(self.s[-1])
        self.s_f1 = float(np.interp(self.z_f1, self.zg, self.s))   # seam length where the frill ends

    def radius(self, z):
        return self.r0 + (self.r1 - self.r0) * np.asarray(z) / self.L

    def pitch(self, z):
        t = np.clip(np.asarray(z) / self.Ls, 0, 1) ** PITCH_CURVE
        return PITCH_BASE + (PITCH_TIP - PITCH_BASE) * t

    def _fade(self, z):
        if TRANSITION <= 0:
            return np.ones_like(np.asarray(z, dtype=float))
        T = min(TRANSITION, self.Ls - self.zmin)
        u = np.clip((np.asarray(z) - (self.Ls - T)) / T, 0, 1)
        return 1 - u

    def Q(self, theta):
        """Height of the seam edge at angle theta (the same curve, one turn up per 2 pi)."""
        theta = np.asarray(theta, dtype=float)
        below = self.zmin + theta * float(self.pitch(self.zmin)) / (2 * math.pi)
        return np.where(theta < 0, below, np.interp(theta, self.thg, self.zg))

    def flat(self, theta, z):
        """Unrolled position (x, y) of the point at angle theta and height z."""
        rho = self.rho0 - np.asarray(z) * self.slant / self.L
        phi = np.asarray(theta) * self.sing
        return np.column_stack([rho * np.cos(phi), rho * np.sin(phi)])

    def at_s(self, s):
        """Angle and height of the seam at arclength s from its start."""
        return float(np.interp(s, self.s, self.thg)), float(np.interp(s, self.s, self.zg))

    def edge_frame(self, s, top):
        """Flat position and direction of the seam's bottom edge (top=False) or top edge (top=True) at arclength s."""
        d = 0.5
        pts = []
        for ss in (s - d, s + d):
            th, z = self.at_s(min(max(ss, 0), self.s_total))
            pts.append(self.flat(th - (2 * math.pi if top else 0), z)[0])
        return (pts[0] + pts[1]) / 2, unit(pts[1] - pts[0])

    def strip_outline(self, n=2500):
        a = -2 * math.pi
        th1 = np.linspace(a, self.theta_c, n)
        th2 = np.linspace(self.theta_c, self.theta_end, max(n // 4, 50))
        th = np.concatenate([th1, th2[1:]])
        bottom = self.flat(th, np.clip(self.Q(th), self.zmin, self.Ls))
        top1 = self.flat(th1, np.clip(self.Q(th1 + 2 * math.pi), self.zmin, self.Ls))
        top2 = self.flat(th2, self.L + 0 * th2)                         # the tip opening: one full turn
        top = np.vstack([top1, [self.flat(self.theta_c, self.L)[0]], top2])
        return np.vstack([bottom, top[::-1]])


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


# ----------------------------------------------------------------------------- pieces
class Piece:
    def __init__(self, name):
        self.name, self.items = name, []

    def add(self, kind, pts, text=None):
        self.items.append((kind, np.asarray(pts, float), text))


def rotate(pts, ang):
    c, s = math.cos(ang), math.sin(ang)
    return pts @ np.array([[c, s], [-s, c]])


def build():
    c = Cone()
    warn = []
    outline = Polygon(c.strip_outline()).buffer(0)
    body = outline.buffer(SEAM, join_style=2, mitre_limit=4)
    if CUFF_IN_STRIP:                                     # no seam allowance on the open end of the cuff
        body = body.intersection(Point(0, 0).buffer(c.rho_bottom, 256))
    # --- alignment tabs along the spiral seam, positions measured from where the frill starts (rel)
    frill_len = c.s_f1 - c.s_f0
    h = TAB_SIZE / 2
    rel = tab_positions(h, frill_len - 3 * h, TAB_SPACING)                       # on the frill (clear of the straight-seam tabs)
    below_hi = c.s_f0 - 1.5 * TAB_SIZE                                           # plain seam below the frill
    plain = [x - c.s_f0 for x in tab_positions(50.0, below_hi, TAB_SPACING)] if below_hi >= 50.0 else []   # not in the open-end corner
    rel_all = sorted(set(round(x, 6) for x in plain + rel))
    cone = Piece("cone")
    squares, labels = [], []
    for i, r_ in enumerate(rel_all, start=1):
        s = c.s_f0 + r_
        for top in (False, True):
            p, t = c.edge_frame(s, top)
            n = outward(p, t, outline)
            squares.append(tab_square(p, t, n, SEAM, TAB_SIZE))
            labels.append((p + n * (SEAM + h), str(i)))
    S = c.L - c.Ls                                         # the straight seam: the two radial edges at the end
    if S > 1e-6:
        for j, z in enumerate([c.Ls + x for x in tab_positions(3 * h, S - h, TAB_SPACING)], start=1):
            for th in (c.theta_end, c.theta_c):
                p = c.flat(th, z)[0]
                t = unit(c.flat(th, z + 0.5)[0] - c.flat(th, z - 0.5)[0])
                n = outward(p, t, outline)
                squares.append(tab_square(p, t, n, SEAM, TAB_SIZE))
                labels.append((p + n * (SEAM + h), f"S{j}"))
    cut = unary_union([body] + squares)
    # --- notches in the seam allowance along the two curved edges: closer together toward the tip
    n_notches = 0
    depth = min(NOTCH_DEPTH, SEAM - 2.0)
    if depth > 0.5:
        if NOTCH_SPACING_BASE < 3 or NOTCH_SPACING_TIP < 3:
            raise SystemExit("Notch spacing must be at least 3 mm.")
        tab_s = [c.s_f0 + x for x in rel_all]
        half_w = (depth + 2.0) * math.tan(math.radians(25))               # a 50 degree V
        cutters = []
        sn = 15.0
        while sn < c.s_total - 15.0:
            if all(abs(sn - ts) > 1.2 * TAB_SIZE for ts in tab_s):
                for top in (False, True):
                    p, t = c.edge_frame(sn, top)
                    n = outward(p, t, outline)
                    cutters.append(Polygon([p + n * (SEAM - depth), p + n * (SEAM + 2.0) - t * half_w, p + n * (SEAM + 2.0) + t * half_w]))
                n_notches += 2
            sn += NOTCH_SPACING_BASE + (NOTCH_SPACING_TIP - NOTCH_SPACING_BASE) * min(sn / c.s_total, 1.0)
        if cutters:
            cut = cut.difference(unary_union(cutters))
    if cut.geom_type != "Polygon" or len(cut.interiors) > 0:
        warn.append("The cut outline touches itself (the tabs or seam allowance of neighbouring turns meet, probably "
                    "near the tip). Make the tip wider, the pitch looser or the seam allowance smaller.")
        if cut.geom_type != "Polygon":
            cut = max(cut.geoms, key=lambda g: g.area)
    cone.add("cut", np.array(cut.exterior.coords))
    cone.add("sew", np.array(outline.exterior.coords))
    if CUFF_IN_STRIP:
        tc = np.linspace(c.theta_z0 - 2 * math.pi, c.theta_z0, 300)
        cone.add("mark", c.flat(tc, 0 * tc))                   # the cuff line (top of the cuff)
    for p, txt in labels:
        cone.add("label", [p], txt)
    pieces = [cone]
    # --- the frill: one long straight strip, solid along the seam, fringe on the free part
    F = RUFFLE_WIDTH - SEAM                                # fringe length (the part that stands out)
    W = RUFFLE_WIDTH
    n_slits = max(1, round(frill_len / FRINGE_WIDTH))
    strand = frill_len / n_slits
    rect = Polygon([[0, 0], [frill_len, 0], [frill_len, W], [0, W]])
    tabs = []
    labs = []
    for i, r_ in enumerate(rel_all, start=1):
        if 0 <= r_ <= frill_len:
            tabs.append(tab_square(np.array([r_, 0.0]), np.array([1.0, 0.0]), np.array([0.0, -1.0]), 0.0, TAB_SIZE))
            labs.append((np.array([r_, -h]), str(i)))
    fcut = unary_union([rect] + tabs)
    shift = np.array([0.0, TAB_SIZE])                      # tabs hang below the strip, so lift everything
    pc = Piece("frill")
    ring = [tuple(q) for q in fcut.exterior.coords]
    loop = []                                              # ONE closed loop: each slit is walked down and back up on the free edge
    for (xa, ya), (xb, yb) in zip(ring[:-1], ring[1:]):
        loop.append((xa, ya))
        if abs(ya - W) < 1e-9 and abs(yb - W) < 1e-9 and xa != xb:
            ks = [k for k in range(1, n_slits) if min(xa, xb) < k * strand < max(xa, xb)]
            ks.sort(key=lambda k: abs(k * strand - xa))
            for k in ks:
                x = k * strand
                loop += [(x, W), (x, SEAM), (x, W)]
    loop.append(ring[-1])
    pc.add("cut", np.array(loop) + shift)
    pc.add("sew", np.array([[0, SEAM], [frill_len, SEAM]]) + shift)
    for p, txt in labs:
        pc.add("label", [p + shift], txt)
    pc.w, pc.h = frill_len, W + TAB_SIZE
    frills = [pc]
    pieces += frills
    circ = math.pi * BASE_DIAMETER
    if not CUFF_IN_STRIP:                                   # separate cuff band
        cw, ch = circ + 2 * SEAM, CUFF_HEIGHT + SEAM + HEM
        pc = Piece("cuff")
        pc.add("cut", [[0, 0], [cw, 0], [cw, ch], [0, ch], [0, 0]])
        pc.add("sew", [[SEAM, HEM], [cw - SEAM, HEM], [cw - SEAM, ch - SEAM], [SEAM, ch - SEAM], [SEAM, HEM]])
        pc.w, pc.h = cw, ch
        pieces.append(pc)
    # --- numbers and checks
    xs, ys = np.array(outline.minimum_rotated_rectangle.exterior.coords).T
    sides = sorted([math.hypot(xs[1] - xs[0], ys[1] - ys[0]), math.hypot(xs[2] - xs[1], ys[2] - ys[1])])
    cb = cut.bounds
    if sides[0] + 2 * SEAM > FABRIC_WIDTH:
        warn.append(f"The cone strip is {sides[0] + 2 * SEAM:.0f} mm across (tightest fit) and does not fit the {FABRIC_WIDTH / 25.4:.0f} in ({FABRIC_WIDTH:.0f} mm) fabric.")
    r_end = float(c.radius(c.z_f1))
    if F > r_end:
        warn.append(f"The frill stands out {F:.0f} mm, more than the cone's radius ({r_end:.0f} mm) where the spiral ends, "
                    "so frill from opposite sides of the cone will overlap there (soft fringe, so it may be fine).")
    if frill_len > FABRIC_WIDTH * 4:
        warn.append("The frill strip is very long.")
    d_bottom = 2 * float(c.radius(c.zmin))
    if CUFF_IN_STRIP and d_bottom - BASE_DIAMETER > 6:
        warn.append(f"The cuff is part of the cone, so it flares: {BASE_DIAMETER:.0f} mm across at the cuff line (the tube fit) "
                    f"and {d_bottom:.0f} mm at the open end. CUFF_IN_STRIP = 0 gives a straight separate band.")
    z0 = float(np.interp(0.0, c.zg, c.thg))
    info = dict(pieces=len(pieces), turns=c.theta_end / (2 * math.pi), seam_total=c.s_total, frill_len=frill_len,
                n_slits=n_slits, strand=strand, F=F, frill_w=W,
                straight=S, tab_count=len(rel_all), n_notches=n_notches, strip_tight=sides[0] + 2 * SEAM, strip_long=sides[1] + 2 * SEAM,
                bbox=(cb[2] - cb[0], cb[3] - cb[1]), half_angle=math.degrees(math.asin(c.sing)),
                tip_circ=math.pi * TIP_DIAMETER, d_bottom=d_bottom, circ=circ,
                gain0=float(c.Q(z0 + 2 * math.pi) - c.Q(z0)), warnings=warn)
    return c, outline, cut, pieces, info


def report(info):
    L = ["SPIRAL-CONE POLYP: flat pattern numbers (millimetres)", "", "Settings:"]
    L += [f"  {k:<16} {v:g}" for k, v in settings().items()]
    L += ["", "Results:",
          f"  Cone half-angle                 {info['half_angle']:.1f} deg",
          f"  Turns of the spiral seam        {info['turns']:.2f} (cuff included)",
          f"  Height gained per turn          {info['gain0']:.0f} mm at the cuff line (the PITCH settings are the rate at one exact height)",
          f"  Spiral seam length              {info['seam_total']:.0f} mm; the frill covers {info['frill_len']:.0f} mm of it",
          f"  Straight seam                   {info['straight']:.0f} mm",
          f"  Cone strip, cut size            bounding box {info['bbox'][0]:.0f} x {info['bbox'][1]:.0f} mm, "
          f"tightest rectangle {info['strip_tight']:.0f} x {info['strip_long']:.0f} mm",
          f"  Frill                           one strip {info['frill_len']:.0f} x {info['frill_w']:.0f} mm; solid {SEAM:g} mm seam allowance, "
          f"{info['F']:.0f} mm of fringe slit into {info['n_slits']} strands {info['strand']:.1f} mm wide"]
    L.append("  Cuff                            " + (
        f"part of the cone strip: {BASE_DIAMETER:.0f} mm across at the cuff line, {info['d_bottom']:.0f} mm at the open end, "
        f"{CUFF_HEIGHT:g} mm tall, no seam allowance on the open end" if CUFF_IN_STRIP
        else f"separate band, ring {info['circ']:.0f} mm around"))
    L.append(f"  Seam allowance notches          {info['n_notches']} V notches (depth {min(NOTCH_DEPTH, SEAM - 2.0):g} mm) on the curved edges, "
             f"every {NOTCH_SPACING_BASE:g} mm at the base closing to every {NOTCH_SPACING_TIP:g} mm at the tip end"
             if info["n_notches"] else "  Seam allowance notches          none")
    L += [f"  Alignment tabs                  {TAB_SIZE:g} mm squares: {info['tab_count']} numbered tabs along the spiral seam "
          f"(on both cone edges, and on the frill where it covers), S1.. on the straight seam",
          f"  Tip                             " + ("a point (seam allowance still goes round it)" if TIP_DIAMETER <= 0 else f"open, circumference {info['tip_circ']:.0f} mm"),
          f"  Pieces to cut                   {info['pieces']}", ""]
    L += ["Checks:"] + (["  " + w for w in info["warnings"]] or ["  none"])
    return "\n".join(L)


# ----------------------------------------------------------------------------- layout and drawing
def layout(cut, pieces):
    """Offsets (dx, dy) of each piece on the sheet, and the sheet height."""
    b = cut.bounds
    place = {"cone": (-b[0] + 25, -b[1] + 25)}
    width = max(b[2] - b[0], 750.0)
    y0 = (b[3] - b[1]) + 75
    x = y = rowh = 0.0
    for p in pieces[1:]:
        if x + p.w > width and x > 0:
            x, y, rowh = 0.0, y + rowh + 40, 0.0
        place[p.name] = (25 + x, y0 + y)
        x += p.w + 40
        rowh = max(rowh, p.h)
    return place, y0 + y + rowh + 75


def title(name):
    return {"cone": "CONE STRIP (cut 1)", "cuff": "CUFF BAND (cut 1)",
            "frill": "FRILL STRIP (cut 1). Sew along the blue line; the slits make the fringe"}[name]


def export_items(cut, pieces, detailed):
    """Everything an export file draws, at true size in mm, y pointing down, shifted so the drawing starts 10 mm in
    from the corner. detailed=False keeps only the cut lines (what the laser follows): one closed outline per piece (the frill loop doubles back along each slit).
    Returns (items, width, height); items are (kind, points, text) with kind cut / sew / mark / label / title."""
    place, _ = layout(cut, pieces)
    items = []
    for p in pieces:
        dx, dy = place[p.name]
        for k, a, t in p.items:
            if k != "cut" and not detailed:
                continue
            items.append((k, a + np.array([dx, dy]), t))
        if detailed:
            bx, by = (cut.bounds[0] + 5, cut.bounds[1] + 12) if p.name == "cone" else (0.0, -5.0)
            items.append(("title", np.array([[bx + dx, by + dy]]), title(p.name)))
    allp = np.vstack([a for k, a, t in items])
    lo = allp.min(axis=0) - 10.0
    hi = allp.max(axis=0) + 10.0
    if detailed:
        hi[0] = max(hi[0], lo[0] + 90.0)
    items = [(k, a - lo, t) for k, a, t in items]
    return items, float(hi[0] - lo[0]), float(hi[1] - lo[1])


def write_svg(path, cut, pieces, detailed):
    items, w, h = export_items(cut, pieces, detailed)
    style = {"cut": 'stroke="#d00000" stroke-width="0.5" fill="none"',
             "sew": 'stroke="#1d4ed8" stroke-width="0.4" stroke-dasharray="3 2" fill="none"',
             "mark": 'stroke="#777" stroke-width="0.4" stroke-dasharray="1.2 3" fill="none"'}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.3f} {h:.3f}">',
           "<!-- Units are millimetres, true size. " + ("Red = cut, blue dashed = sew line, grey dotted = cuff line. Squares are alignment tabs. -->"
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


def write_pdf(path, cut, pieces, detailed):
    """True-size PDF: the page is exactly as big as the drawing (1 PDF point = 1/72 inch = 0.3528 mm), no margins
    added by the program, no grid, no scales. Laser version: black 0.001 in lines, nothing else."""
    items, w, h = export_items(cut, pieces, detailed)
    fig = plt.figure(figsize=(w / 25.4, h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.axis("off")
    fig.patch.set_visible(False)                      # no white background rectangle for the laser software to pick up
    # laser PDF: pure black, 0.001 in wide (= 0.072 pt), which is the line the cutter software expects
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


def write_dxf(path, cut, pieces, detailed):
    """Laser/CAD file, true size, units = millimetres. Plain ASCII DXF (R12 style), no extra libraries.
    Layer CUT (one closed outline per piece); detailed adds SEW, MARK, LABELS, TITLES.
    The y axis points up (the SVG/PDF one points down), so it looks the same as on the page."""
    items, w, h = export_items(cut, pieces, detailed)
    code = []

    def put(c, v):
        code.append(f"{c}\n{v}")

    ents = []
    for k, a, t in items:
        if k == "label" or k == "title":
            ents.append(("LABELS" if k == "label" else "TITLES", "text", a[0], t))
            continue
        closed = len(a) > 3 and np.allclose(a[0], a[-1])
        layer = {"cut": "CUT" if closed else "SLITS", "sew": "SEW", "mark": "MARK"}[k]
        ents.append((layer, "poly", a[:-1] if closed else a, closed))
    put(0, "SECTION"); put(2, "HEADER")
    put(9, "$ACADVER"); put(1, "AC1009")
    put(9, "$INSUNITS"); put(70, 4)                                     # 4 = millimetres
    put(9, "$MEASUREMENT"); put(70, 1)                                  # 1 = metric
    put(9, "$EXTMIN"); put(10, "0.0"); put(20, f"{-h:.4f}"); put(30, 0)
    put(9, "$EXTMAX"); put(10, f"{w:.4f}"); put(20, "0.0"); put(30, 0)
    put(0, "ENDSEC")
    layers = {"CUT": 1, "SLITS": 1, "SEW": 5, "MARK": 8, "LABELS": 1, "TITLES": 8}
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


def draw_png_outline(path, cut, pieces):
    """Preview of the laser view: the flat pieces and only their cut lines (axes in mm and inches to read sizes)."""
    items, w, h = export_items(cut, pieces, False)
    fig = plt.figure(figsize=(10, max(4.0, 10 * h / w + 1.2)))
    ax = fig.add_subplot(111)
    for k, a, t in items:
        ax.plot(a[:, 0], a[:, 1], color="#d00000", lw=0.9)
    ax.set_xlim(0, w); ax.set_ylim(h, 0); ax.set_aspect("equal"); ax.grid(alpha=.2)
    ax.set_xlabel("mm"); ax.set_ylabel("mm")
    sx = ax.secondary_xaxis("top", functions=(lambda v: v / 25.4, lambda v: v * 25.4)); sx.set_xlabel("inches")
    sy = ax.secondary_yaxis("right", functions=(lambda v: v / 25.4, lambda v: v * 25.4)); sy.set_ylabel("inches")
    ax.set_title("Laser cut view: only the lines the laser follows (the frill is one closed loop that doubles back along each slit)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def draw_png(path, c, outline, cut, pieces, info):
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1])
    ax = fig.add_subplot(gs[0, 0])
    place, ymax = layout(cut, pieces)
    col = {"cut": ("#d00000", "-", 1.1), "sew": ("#1d4ed8", "--", 0.9), "mark": ("#777", ":", 1.0)}
    for p in pieces:
        dx, dy = place[p.name]
        for k, a, t in p.items:
            if k == "label":
                ax.text(a[0][0] + dx, a[0][1] + dy, t, fontsize=6, ha="center", va="center", color="#d00000")
            else:
                ax.plot(a[:, 0] + dx, a[:, 1] + dy, color=col[k][0], ls=col[k][1], lw=col[k][2])
        if p.name == "cone":
            o = np.array(outline.exterior.coords)
            ax.fill(o[:, 0] + dx, o[:, 1] + dy, color="#dbe7f5", zorder=0)
            ax.text(cut.bounds[0] + dx + 8, cut.bounds[1] + dy + 20, "CONE STRIP", fontsize=9, color="#444")
        else:
            ax.text(dx, dy - 10, title(p.name), fontsize=8, color="#444")
    ax.set_aspect("equal"); ax.invert_yaxis(); ax.grid(alpha=.2); ax.set_xlabel("mm"); ax.set_ylabel("mm")
    sx = ax.secondary_xaxis("top", functions=(lambda v: v / 25.4, lambda v: v * 25.4)); sx.set_xlabel("inches")
    sy = ax.secondary_yaxis("right", functions=(lambda v: v / 25.4, lambda v: v * 25.4)); sy.set_ylabel("inches")
    ax.set_title("Flat pieces. Red = cut, blue dashed = sew, numbered squares = alignment tabs that go together", fontsize=10)
    a3 = fig.add_subplot(gs[0, 1], projection="3d")
    zz = np.linspace(c.zmin, c.L, 40); tt = np.linspace(0, 2 * math.pi, 60)
    Z, T = np.meshgrid(zz, tt)
    R = c.radius(Z)
    a3.plot_surface(R * np.cos(T), R * np.sin(T), Z, color="#dbe7f5", alpha=0.45, linewidth=0, shade=True)
    th, z = c.thg, c.zg
    r = c.radius(z)
    a3.plot(r * np.cos(th), r * np.sin(th), z, color="#1d4ed8", lw=1.2)
    zs = np.array([c.Ls, c.L]); rs = c.radius(zs)
    a3.plot(rs * math.cos(c.theta_end), rs * math.sin(c.theta_end), zs, color="#1d4ed8", lw=2)   # the straight seam
    F = info["F"]
    for k in range(0, len(th), 40):
        if z[k] < FRILL_START or z[k] > c.z_f1:
            continue
        n = np.array([c.cosg * math.cos(th[k]), c.cosg * math.sin(th[k]), c.sing])
        p0 = np.array([r[k] * math.cos(th[k]), r[k] * math.sin(th[k]), z[k]])
        a3.plot(*zip(p0, p0 + F * n), color="#c4492f", lw=0.9)
    a3.plot(c.r0 * np.cos(tt), c.r0 * np.sin(tt), 0 * tt, color="k", lw=1)
    m = max(c.L, 2 * float(c.radius(c.zmin)) + 2 * F) / 2
    a3.set_xlim(-m, m); a3.set_ylim(-m, m); a3.set_zlim(c.zmin, c.L)
    a3.set_box_aspect((1, 1, (c.L - c.zmin) / (2 * m)))
    a3.view_init(18, -60)
    a3.set_title(f"Finished cone: {info['turns']:.1f} turns, then a straight seam for the last {info['straight']:.0f} mm.\n"
                 f"Blue = seam, red lines = frill fringe ({F:.0f} mm out, from {FRILL_START:g} mm up to {FRILL_END_FROM_TIP:g} mm from the tip)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def make(out, name="spiral-cone"):
    os.makedirs(out, exist_ok=True)
    c, outline, cut, pieces, info = build()
    for view, detailed in (("detailed", True), ("outline", False)):     # the two views the page can show, each exported three ways
        for ext, fn in (("svg", write_svg), ("pdf", write_pdf), ("dxf", write_dxf)):
            fn(os.path.join(out, f"{name}-{view}.{ext}"), cut, pieces, detailed)
    draw_png_outline(os.path.join(out, name + "-outline.png"), cut, pieces)
    draw_png(os.path.join(out, name + ".png"), c, outline, cut, pieces, info)
    text = report(info)
    with open(os.path.join(out, name + ".txt"), "w") as f:
        f.write(text + "\n")
    return info, text


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="out")
    ap.add_argument("--name", default="spiral-cone")
    a = ap.parse_args()
    apply_overrides(os.environ.get("CONE"))
    info, text = make(a.out, a.name)
    print(text)


if __name__ == "__main__":
    main()
