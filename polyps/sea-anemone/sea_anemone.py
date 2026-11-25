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
MID_HEIGHT = 125.0          # the central control point of the tube's cross-section: how far up from the bottom
MID_DIAMETER = 130.0        # ... its diameter. Two straight-sided cones (cut-off cones) stack: bottom to centre, centre to top
DIAMETER_TOP = 150.0        # ASSUMED. Slightly flared top. The cap disk and the frill ring match this
FRILL_STRIP_LENGTH = 0.0    # length of the frill strip round the ring. 0 = exactly the top circumference (pi x top diameter). More = it gathers
FRILL_LENGTH = 48.0         # ASSUMED. How far the frill stands out (the fringe). The strip's cut width is this + seam allowance + solid band
FRINGE_WIDTH = 6.0          # the standing-out part of the frill is slit into strands this wide
FRILL_WAVE = 3.0            # ASSUMED. How wavy the fringe strands are: height of the wave in mm (0 = straight). All strands wave the same way, so they still nest
FRILL_WAVE_LENGTH = 40.0    # ASSUMED. Length of one wave along a strand
FRILL_BAND = 0.0            # solid (unslit) band between the sew line and the fringe. 0 = fringe starts at the sew line
FRILL_NOTCH_DEPTH = 0.0     # V notches in the frill's seam allowance (0 = none: Remy chose a plain strip for easier handling, accepting some bunching; was 9 mm = 3/8 in, leaving 3 mm)
FRILL_NOTCHES_BETWEEN_TABS = 7.0  # ASSUMED. How many notches go between each pair of neighbouring ring tabs on the frill (0 = none). Their width is worked out from the circle
SEAM = 12.0                 # seam allowance on every edge
TUBE_NOTCH_DEPTH = 6.0      # Remy: about 6 mm. V notches in the allowance of the curved (arc) edges of the two cone pieces: the ring seam between them and the top edge (0 = none). Their straight side edges and the open bottom edge have none
TUBE_NOTCHES_BETWEEN_TABS = 3.0   # ASSUMED. How many notches go between each pair of neighbouring ring tabs along those arc edges
FABRIC_WIDTH = 1470.0       # ASSUMED usable fabric width (about 58 in), for the fit check
TAB_SIZE = 12.0             # alignment tab width along the edge (and the width of the frill tabs)
TAB_LENGTH = 12.0           # how far alignment tabs reach out from the seam allowance (12 = square tabs)
LASER_BED_SHORT = 609.6     # laser bed, short side in mm (24 in)
LASER_BED_LONG = 914.4      # laser bed, long side in mm (36 in)
NEST_GAP = 3.0             # space between pieces on the laser sheet (Laser cut view and its exports). The Detailed view keeps its own readable layout
FRILL_TAB_LENGTH = 30.0     # length of the tabs on the frill (2.5 x the normal tab size). Fold them over to make loops for a hoop. Their width is TAB_SIZE
TABS_LOWER_SEAM = 2.0       # number of alignment tabs along each straight seam edge of the lower cone (the same number on both edges, so they pair up), evenly spaced
TABS_MID_RING = 3.0         # number of tabs round the ring seam between the two cones (on both arcs), evenly spaced
TABS_UPPER_SEAM = 2.0       # number of tabs along each straight seam edge of the upper cone
TABS_TOP_RING = 4.0         # number of tabs round the top ring: the top arc of the upper cone, the cap and the frill all get this many, matching
CAP_HOLE_DIAMETER = 6.0     # hole in the centre of the cap disk for the string (0 = none)
AIR_HOLE_DIAMETER = 0.5     # tiny holes round the top of the upper cone that blow air onto the frill (0 or count 0 = none)
AIR_HOLE_DISTANCE = 6.0     # how far below the top seam (along the cone surface, from the sew line) the air holes sit
AIR_HOLE_COUNT = 80.0       # how many air holes, evenly spaced round the top
GUIDE_TABS = 4.0            # long string-guide tabs at the ring seam between the cones: the total, shared out alternately between the two cones so they cannot overlap in the flat pattern
GUIDE_TAB_WIDTH = 6.0       # width of the stem of a guide tab
GUIDE_RING_DIAMETER = 12.0  # diameter of the round end of a guide tab
GUIDE_HOLE_DIAMETER = 4.0   # hole in that round end; the tips overlap on the tube's axis and are pinned together there
GUIDE_TAB_EXTRA = 0.0       # extra length of the guide tabs: 0 = the hole centre lands exactly on the axis (tab length from the sew line = the radius at the ring seam)
SACRIFICE_STRIP_WIDTH = 2.0       # sacrificial strip along the free ends of the fringe strands: it holds all the loose strands together while you handle and sew the frill; you cut it off afterwards (0 = none)
SACRIFICE_CONNECTOR_WIDTH = 1.5   # width of the little bridge that joins each strand tip to the strip
SACRIFICE_CONNECTOR_LENGTH = 1.5  # length of that bridge: the gap between a strand tip and the strip
SLIT_SINGLE_LINE = 1.0            # 1 = every slit between two fringe strands is cut ONCE, as a single open line (halves the cutting path of the slits); 0 = the older way: slits walked down and back up inside closed loops (each cut twice)
PATTERN_METHOD = 0.0              # 0 = two stacked cones (exact flat pattern); 1 = two hourglass-shaped halves (two vertical seams, not exact: bunching at the neck)
TABS_HALF_SEAM = 3.0              # hourglass method: number of alignment tabs along each seam edge of a half, evenly spaced

NAMES = ["HEIGHT", "DIAMETER_BOTTOM", "DIAMETER_TOP", "MID_HEIGHT", "MID_DIAMETER", "FRILL_STRIP_LENGTH", "FRILL_LENGTH", "FRINGE_WIDTH",
         "FRILL_WAVE", "FRILL_WAVE_LENGTH", "FRILL_BAND", "FRILL_NOTCH_DEPTH", "FRILL_NOTCHES_BETWEEN_TABS", "SEAM", "TUBE_NOTCH_DEPTH", "TUBE_NOTCHES_BETWEEN_TABS",
         "FABRIC_WIDTH", "LASER_BED_SHORT", "LASER_BED_LONG", "NEST_GAP", "TAB_SIZE", "TAB_LENGTH", "FRILL_TAB_LENGTH", "TABS_LOWER_SEAM", "TABS_MID_RING", "TABS_UPPER_SEAM", "TABS_TOP_RING",
         "CAP_HOLE_DIAMETER", "AIR_HOLE_DIAMETER", "AIR_HOLE_DISTANCE", "AIR_HOLE_COUNT", "GUIDE_TABS", "GUIDE_TAB_WIDTH", "GUIDE_RING_DIAMETER", "GUIDE_HOLE_DIAMETER", "GUIDE_TAB_EXTRA",
         "SACRIFICE_STRIP_WIDTH", "SACRIFICE_CONNECTOR_WIDTH", "SACRIFICE_CONNECTOR_LENGTH", "SLIT_SINGLE_LINE", "PATTERN_METHOD", "TABS_HALF_SEAM"]


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


# ----------------------------------------------------------------------------- the tube: two stacked cones
class Frustum:
    """One cut-off cone (bottom radius r_a, top radius r_b, axial height h) flattened EXACTLY: a sector of a ring with straight
    side edges (the seam) and arcs for the top and bottom edges, like a paper party hat with the tip cut off. A cylinder
    (r_a = r_b) is a plain rectangle."""

    def __init__(self, r_a, r_b, h, frac=1.0):
        self.r_a, self.r_b, self.h, self.frac = r_a, r_b, h, frac     # frac = the part of the way round the cone this piece covers (1 = all, 0.5 = a half)
        self.L = math.hypot(h, r_b - r_a)                          # slant length = length of the straight seam
        d = r_b - r_a
        self.cyl = abs(d) < 1e-6
        if self.cyl:
            self.theta, self.rho_a, self.rho_b = None, None, None
        else:
            self.rho_a = r_a * self.L / abs(d)                     # flat distance from the cone's tip to the bottom ring
            self.rho_b = r_b * self.L / abs(d)
            self.theta = 2 * math.pi * abs(d) / self.L * frac      # angle of the sector

    def ring_point(self, which, f, dist=0.0):
        """Flat position of the point a fraction f (0..1) of the way round the bottom ('a') or top ('b') ring, optionally `dist` mm
        along the cone surface from that ring toward the other ring."""
        r = self.r_a if which == "a" else self.r_b
        if self.cyl:
            y = self.h - dist if which == "a" else dist
            return np.array([-math.pi * r * self.frac + f * 2 * math.pi * r * self.frac, y])
        rho = self.rho_a if which == "a" else self.rho_b
        other = self.rho_b if which == "a" else self.rho_a
        rho = rho + (dist if other > rho else -dist)
        phi = -self.theta / 2 + f * self.theta
        sgn = -1.0 if self.r_b > self.r_a else 1.0                   # widening upward: the tip is below the piece, so "up" is -y
        return np.array([rho * math.sin(phi), sgn * rho * math.cos(phi)])

    def ring_frame(self, which, f):
        d = 1e-4
        p0, p1 = self.ring_point(which, f - d), self.ring_point(which, f + d)
        return self.ring_point(which, f), unit(p1 - p0)

    def side_point(self, side, lam):
        """Point on the straight seam edge (side -1 left, +1 right), lam mm along it from the bottom ring."""
        f = 0.0 if side < 0 else 1.0
        pa, pb = self.ring_point("a", f), self.ring_point("b", f)
        return pa + (pb - pa) * (lam / self.L)

    def side_frame(self, side, lam):
        f = 0.0 if side < 0 else 1.0
        pa, pb = self.ring_point("a", f), self.ring_point("b", f)
        return self.side_point(side, lam), unit(pb - pa)

    def outline(self, n=400):
        fs = np.linspace(0, 1, n)
        bottom = np.array([self.ring_point("a", f) for f in fs])
        top = np.array([self.ring_point("b", f) for f in fs])
        return np.vstack([bottom, top[::-1]])                          # bottom left to right, up the right edge, top right to left, down the left edge

    def flush_bottom(self, body):
        """Remove the seam allowance beyond the bottom ring (the open bottom edge has none)."""
        if self.cyl:
            return body.intersection(Polygon([(-1e4, self.h), (1e4, self.h), (1e4, -1e4), (-1e4, -1e4)]))
        disc = Point(0, 0).buffer(self.rho_a, 1024)
        return body.difference(disc) if self.r_b > self.r_a else body.intersection(disc)


class HourglassHalf:
    """One half of the whole tube (half the circumference at every height) as a single hourglass-shaped piece: the half of the lower
    cone and the half of the upper cone, each flattened exactly, joined at the middle of the neck. The two neck arcs curve
    opposite ways, so at the sides they overlap a little: that fabric is lost, the seam edges come out shorter than the centre line
    and the fabric bunches round the neck. NOT exact, by design. The seam edges are straight up to where the two cones' edges cross
    (the pinch of the neck) and then straight again."""

    def __init__(self, rb, rm, rt, h1, h2):
        self.lo, self.up = Frustum(rb, rm, h1, 0.5), Frustum(rm, rt, h2, 0.5)
        self.shift = np.array([0.0, self.lo.ring_point("b", 0.5)[1] - self.up.ring_point("a", 0.5)[1]])       # upper half moved so the middles of the neck arcs touch
        self.r_a, self.r_b, self.h, self.cyl = rb, rt, h1 + h2, False
        self.left, self.right = self._edge(0.0), self._edge(1.0)
        seg = np.hypot(*np.diff(self.left, axis=0).T)
        self.cum = np.concatenate([[0.0], np.cumsum(seg)])
        self.L = float(self.cum[-1])                                    # length of a seam edge
        self.S_centre = self.lo.L + self.up.L                           # length up the middle of the half
        self.overlap = float(abs(self.lo.ring_point("b", 0.0)[1] - (self.up.ring_point("a", 0.0) + self.shift)[1]))   # how far the two neck arcs overlap at the sides

    def _edge(self, f):
        bl, n1 = self.lo.ring_point("a", f), self.lo.ring_point("b", f)
        n2, tl = self.up.ring_point("a", f) + self.shift, self.up.ring_point("b", f) + self.shift
        d1, d2 = n1 - bl, tl - n2
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) > 1e-12:
            t = ((n2[0] - bl[0]) * d2[1] - (n2[1] - bl[1]) * d2[0]) / den
            u = ((n2[0] - bl[0]) * d1[1] - (n2[1] - bl[1]) * d1[0]) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                return np.array([bl, bl + d1 * t, tl])                  # the two edges cross: the pinch of the neck
        pts = [bl, n1, n2, tl]
        return np.array([q for k, q in enumerate(pts) if k == 0 or np.hypot(*(q - pts[k - 1])) > 1e-9])

    def ring_point(self, which, f, dist=0.0):
        return self.lo.ring_point("a", f, dist) if which == "a" else self.up.ring_point("b", f, dist) + self.shift

    def ring_frame(self, which, f):
        d = 1e-4
        p0, p1 = self.ring_point(which, f - d), self.ring_point(which, f + d)
        return self.ring_point(which, f), unit(p1 - p0)

    def _at(self, side, lam):
        pl = self.left if side < 0 else self.right
        lam = min(max(lam, 0.0), self.L)
        k = min(int(np.searchsorted(self.cum, lam, side="right")) - 1, len(pl) - 2)
        seg = pl[k + 1] - pl[k]
        return pl[k] + seg * ((lam - self.cum[k]) / max(self.cum[k + 1] - self.cum[k], 1e-12)), unit(seg)

    def side_point(self, side, lam):
        return self._at(side, lam)[0]

    def side_frame(self, side, lam):
        return self._at(side, lam)

    def outline(self, n=400):
        fs = np.linspace(0, 1, n)
        bottom = [self.ring_point("a", f) for f in fs]
        top = [self.ring_point("b", f) for f in fs][::-1]
        return np.array(bottom + list(self.right[1:]) + top[1:] + list(self.left[::-1][1:-1]))

    def flush_bottom(self, body):
        return self.lo.flush_bottom(body)


class StackedTube:
    """The tube as two cut-off cones stacked on each other: bottom ring to the central control point, central point to the top."""

    def __init__(self):
        H = HEIGHT
        rb, rm, rt = DIAMETER_BOTTOM / 2, MID_DIAMETER / 2, DIAMETER_TOP / 2
        if H <= 40:
            raise SystemExit("The height must be more than 40 mm.")
        if min(rb, rm, rt) < 10:
            raise SystemExit("Every diameter must be at least 20 mm.")
        if not (20 <= MID_HEIGHT <= H - 20):
            raise SystemExit(f"The central control point must be at least 20 mm from the bottom and the top (height between 20 and {H - 20:g} mm).")
        self.lower = Frustum(rb, rm, MID_HEIGHT)
        self.upper = Frustum(rm, rt, H - MID_HEIGHT)
        self.rb, self.rm, self.rt = rb, rm, rt
        self.S = self.lower.L + self.upper.L                           # fabric length of the tube, bottom to top, along the seams
        self.z = np.linspace(0, H, 600)                                # profile for the 3D picture
        self.r = np.interp(self.z, [0, MID_HEIGHT, H], [rb, rm, rt])


def tab_square(p, t, n, off, size, length=None):
    """A tab on the side n of the edge point p (tangent t): `size` wide along the edge, reaching `length` (default: size) beyond
    `off` from the edge."""
    a, b = off - 5, off + (size if length is None else length)
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


def circle_points(cx, cy, d, n=None):
    """A closed polyline for a circle of diameter d (more points for bigger circles)."""
    n = n or int(min(96, max(12, 8 * d)))
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = np.column_stack([cx + d / 2 * np.cos(a), cy + d / 2 * np.sin(a)])
    return np.vstack([pts, pts[:1]])



def v_notch_open(p, t, n, depth, half_w, out=2.0, reach=40.0):
    """Like v_notch, but the V keeps going straight out past the allowance's edge. A notch right on a corner would otherwise sit
    wholly inside the mitred corner of the allowance and leave a closed hole."""
    w = half_w * (depth + out) / depth
    return Polygon([p + n * (SEAM - depth), p + n * (SEAM + out) - t * w, p + n * (SEAM + reach) - t * w,
                    p + n * (SEAM + reach) + t * w, p + n * (SEAM + out) + t * w])


class Piece:
    def __init__(self, name):
        self.name, self.items = name, []

    def add(self, kind, pts, text=None):
        self.items.append((kind, np.asarray(pts, float), text))


# ----------------------------------------------------------------------------- build
def build():
    T = StackedTube()
    warn = []
    h = TAB_SIZE / 2
    R_top = DIAMETER_TOP / 2
    circ_top = 2 * math.pi * R_top
    circ_mid = 2 * math.pi * T.rm
    n_ring, n_mid = int(round(TABS_TOP_RING)), int(round(TABS_MID_RING))
    n_lo, n_up = int(round(TABS_LOWER_SEAM)), int(round(TABS_UPPER_SEAM))
    hourglass = PATTERN_METHOD >= 0.5
    if hourglass and n_ring % 2:
        n_ring += 1                                                        # each half carries half of the top ring tabs
    if n_ring < 1 or n_mid < 1:
        raise SystemExit("The ring seams need at least 1 tab each (the notches are placed between the tabs).")
    if n_lo < 0 or n_up < 0:
        raise SystemExit("Tab counts cannot be negative.")
    if max(n_ring, n_mid) > 26:
        raise SystemExit("A ring seam can have at most 26 tabs (they are labelled with letters).")
    ring_f = [(i + 0.5) / n_ring for i in range(n_ring)]                 # tab positions round the top ring, as fractions
    ring_lab = [chr(ord("A") + i) for i in range(n_ring)]
    mid_f = [(i + 0.5) / n_mid for i in range(n_mid)]                    # tab positions round the ring seam between the two cones
    mid_lab = [chr(ord("a") + i) for i in range(n_mid)]
    depth = min(TUBE_NOTCH_DEPTH, SEAM - 2.0)
    n_between = int(round(TUBE_NOTCHES_BETWEEN_TABS))
    half_w = max(depth, 0.1) * math.tan(math.radians(25))                # a 50 degree V
    n_air = int(round(AIR_HOLE_COUNT)) if AIR_HOLE_DIAMETER > 0 else 0
    if n_air > 0 and not (0 < AIR_HOLE_DISTANCE < T.upper.L - 2):
        raise SystemExit(f"The air holes must sit between 0 and {T.upper.L - 2:.0f} mm below the top seam (the upper cone is {T.upper.L:.0f} mm along its surface).")
    if hourglass and n_air % 2:
        n_air += 1                                                         # half of the air holes on each half
    n_guide = 0 if hourglass else int(round(GUIDE_TABS))
    if n_guide < 0 or n_guide > 24:
        raise SystemExit("Between 0 and 24 string-guide tabs, please.")
    if n_guide > 0 and (GUIDE_RING_DIAMETER <= GUIDE_HOLE_DIAMETER + 1 or GUIDE_TAB_WIDTH <= 0 or GUIDE_HOLE_DIAMETER <= 0):
        raise SystemExit("A guide tab's round end must be bigger than its hole (and both above zero).")
    # guide tabs: tab j sits at fraction (j + 0.5) / n round the ring seam; even j on the lower cone's top arc, odd j on the upper cone's bottom arc
    guide_lo = [("b", (j + 0.5) / n_guide, f"G{j + 1}") for j in range(n_guide) if j % 2 == 0] if n_guide else []
    guide_up = [("a", (j + 0.5) / n_guide, f"G{j + 1}") for j in range(n_guide) if j % 2 == 1] if n_guide else []
    n_tube_notches = n_skipped = 0
    cone_pieces = []                                                       # (piece, cut polygon, outline polygon)

    def make_cone(F, name, prefix, n_side, bottom_flush, top_f, top_lab, bot_f, bot_lab, guides=(), air_n=0, side_prefix=None):
        """Flat cut piece for one cone. Tabs: numbered along the straight seam; lettered round the arcs that get sewn to
        something. Notches: on the arc edges that have a seam allowance, between the tabs."""
        nonlocal n_tube_notches, n_skipped
        outline = Polygon(F.outline()).buffer(0)
        body = outline.buffer(SEAM, join_style=2, mitre_limit=4)
        if bottom_flush:
            body = F.flush_bottom(body)
        squares, labels = [], []
        side_l = [F.L * (i + 0.5) / n_side for i in range(n_side)]          # evenly spaced along the straight seam
        for i, lam in enumerate(side_l, start=1):
            for side in (-1, 1):
                p, t = F.side_frame(side, lam)
                n = outward(p, t, outline)
                squares.append(tab_square(p, t, n, SEAM, TAB_SIZE, TAB_LENGTH))
                labels.append((p + n * (SEAM + h), f"{prefix if side_prefix is None else side_prefix[0 if side < 0 else 1]}{i}"))
        for which, fr, lab in (("b", top_f, top_lab), ("a", bot_f, bot_lab)):
            if fr is None:
                continue
            for f, lt in zip(fr, lab):
                p, t = F.ring_frame(which, f)
                n = outward(p, t, outline)
                squares.append(tab_square(p, t, n, SEAM, TAB_SIZE, TAB_LENGTH))
                labels.append((p + n * (SEAM + h), lt))
        guide_polys, guide_holes = [], []
        for which, f, lab in guides:                                       # long string-guide tabs: stem + round end with a hole on the tube's axis
            p, t = F.ring_frame(which, f)
            n = outward(p, t, outline)
            ln = T.rm + GUIDE_TAB_EXTRA                                    # from the sew line to the hole centre
            c = p + n * ln
            stem = Polygon([p + t * (-GUIDE_TAB_WIDTH / 2) + n * (SEAM - 5), p + t * (GUIDE_TAB_WIDTH / 2) + n * (SEAM - 5), c + t * (GUIDE_TAB_WIDTH / 2), c + t * (-GUIDE_TAB_WIDTH / 2)])
            gp = unary_union([stem, Point(c).buffer(GUIDE_RING_DIAMETER / 2, 48)])
            guide_polys.append(gp)
            guide_holes.append(circle_points(c[0], c[1], GUIDE_HOLE_DIAMETER))
            labels.append((p + n * (ln * 0.5) + t * (GUIDE_TAB_WIDTH / 2 + 7), lab))
        for gi, gp in enumerate(guide_polys):
            others = squares + [g for gj, g in enumerate(guide_polys) if gj != gi]
            if any(gp.intersects(o) for o in others) or gp.intersects(outline):
                warn.append(f"A string-guide tab on the {name} cone overlaps another tab or the piece itself in the flat pattern. Change the number of guide tabs or of central ring alignment tabs (they should not land on the same spot), or use a smaller tab width.")
                break
        squares = squares + guide_polys                                    # so the notches keep clear of them
        cut = unary_union([body] + squares)
        if depth > 0.5 and n_between > 0:
            tabs_union = unary_union(squares)
            cutters = []
            for which, fr in (("b", top_f), ("a", bot_f)):
                if fr is None:
                    continue
                r_ring = F.r_b if which == "b" else F.r_a
                for f0 in ring_notch_fracs(fr, n_between):
                    # a notch right on the corner (where the straight seam meets the arc) is cut on both ends of the arc: each is half a notch
                    # that reaches into the straight seam's allowance, and the two halves join into one notch when the seam is sewn
                    for f in ([0.0, 1.0] if min(f0, 1 - f0) < 1e-6 else [f0]):
                        corner = min(f, 1 - f) < 1e-6
                        p, t = F.ring_frame(which, f)
                        n = outward(p, t, outline)
                        if corner:                                          # right on a corner the inside/outside test is unreliable: point away from the piece's centre
                            ctr = np.array(outline.centroid.coords[0])
                            if float(np.dot(p - ctr, n)) < 0:
                                n = -n
                        c = (v_notch_open if corner else v_notch)(p, t, n, depth, half_w)
                        if c.distance(tabs_union) < 1.5:
                            n_skipped += 1
                            continue
                        cutters.append(c)
                        n_tube_notches += 1
            if cutters:
                cut = cut.difference(unary_union(cutters))
        if cut.geom_type != "Polygon" or len(cut.interiors) > 0:
            warn.append(f"The {name} piece's cut outline touches itself. Make the seam allowance smaller or move the notches apart.")
            if cut.geom_type != "Polygon":
                cut = max(cut.geoms, key=lambda g: g.area)
        pc = Piece(name)
        pc.add("cut", np.array(cut.exterior.coords))
        pc.add("sew", np.array(outline.exterior.coords))
        for hole in guide_holes:
            pc.add("cut", hole)                                            # holes are separate closed loops inside the piece
        if air_n > 0:                                                      # tiny air holes a set distance below the top seam, evenly spaced round the ring
            for i in range(air_n):
                pc.add("cut", circle_points(*F.ring_point("b", (i + 0.5) / air_n, AIR_HOLE_DISTANCE), AIR_HOLE_DIAMETER))
        for p, txt in labels:
            pc.add("label", [p], txt)
        return pc, cut, outline, len(side_l)

    if not hourglass:
        lower, cut_lo, outline_lo, side_lo = make_cone(T.lower, "lower", "L", n_lo, True, mid_f, mid_lab, None, None, guides=guide_lo)
        upper, cut_up, outline_up, side_up = make_cone(T.upper, "upper", "U", n_up, False, ring_f, ring_lab, mid_f, mid_lab, guides=guide_up, air_n=n_air)
        pieces = [lower, upper]
        parts = [(T.lower, "lower", cut_lo, outline_lo), (T.upper, "upper", cut_up, outline_up)]
        crowd = (("lower cone's straight seam", T.lower.L, n_lo), ("upper cone's straight seam", T.upper.L, n_up),
                 ("central ring seam", circ_mid, n_mid), ("top ring", circ_top, n_ring))
        HG = None
    else:
        # two hourglass halves (identical shape, cut 2): each has half of the top ring tabs and air holes; the straight seams are P (left edge) and Q (right edge)
        HG = HourglassHalf(T.rb, T.rm, T.rt, T.lower.h, T.upper.h)
        n_h = int(round(TABS_HALF_SEAM))
        if n_h < 0:
            raise SystemExit("Tab counts cannot be negative.")
        m = n_ring // 2
        parts, pieces = [], []
        for j in range(2):
            pc, cut_j, outline_j, side_j = make_cone(HG, f"half{j + 1}", "", n_h, True, [(i + 0.5) / m for i in range(m)], ring_lab[j * m:(j + 1) * m], None, None,
                                                     air_n=n_air // 2, side_prefix=("P", "Q"))
            pieces.append(pc)
            parts.append((HG, f"half{j + 1}", cut_j, outline_j))
        side_lo = side_up = n_h
        n_mid = 0
        crowd = (("seam edge of a half", HG.L, n_h), ("top ring", circ_top, n_ring))
    if n_skipped:
        warn.append(f"{n_skipped} tube notch(es) were left out because they would run into a tab. Use fewer notches between tabs.")
    for lab_, ln_, cnt_ in crowd:
        if cnt_ > 0 and ln_ / cnt_ < 1.6 * TAB_SIZE:
            warn.append(f"The {lab_} has {cnt_} tabs in {ln_:.0f} mm: they are only {ln_ / cnt_:.0f} mm apart and will crowd each other. Use fewer or smaller tabs.")
    # --- cap disk
    ccx = ccy = R_top + SEAM
    csq, clab = [], []
    for f, lab in zip(ring_f, ring_lab):
        a = f * 2 * math.pi
        n = np.array([math.cos(a), math.sin(a)])
        p = np.array([ccx, ccy]) + n * R_top
        t = np.array([-n[1], n[0]])
        csq.append(tab_square(p, t, n, SEAM, TAB_SIZE, TAB_LENGTH))
        clab.append((p + n * (SEAM + h), lab))
    ccut = unary_union([Point(ccx, ccy).buffer(R_top + SEAM, 180)] + csq)
    cap = Piece("cap")
    cap.add("cut", np.array(ccut.exterior.coords))
    cap.add("sew", np.array(Point(ccx, ccy).buffer(R_top, 180).exterior.coords))
    for p, txt in clab:
        cap.add("label", [p], txt)
    if CAP_HOLE_DIAMETER > 0:
        if CAP_HOLE_DIAMETER >= 2 * R_top - 10:
            raise SystemExit("The cap's centre hole is too big for the cap.")
        cap.add("cut", circle_points(ccx, ccy, CAP_HOLE_DIAMETER))        # centre hole for the string
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
        ftabs.append(Polygon([(x - h, 5.0), (x + h, 5.0), (x + h, -FRILL_TAB_LENGTH), (x - h, -FRILL_TAB_LENGTH)]))     # frill tab: TAB_SIZE wide, FRILL_TAB_LENGTH long, overlapping the strip by 5 mm
        flabs.append((np.array([x, -FRILL_TAB_LENGTH / 2]), lab))
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
    shift = np.array([0.0, FRILL_TAB_LENGTH])              # tabs hang above the strip's allowance edge, so lift everything
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
    def dedupe(pts):
        out = [pts[0]]
        for q in pts[1:]:
            if math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 1e-9:
                out.append(q)
        if math.hypot(out[-1][0] - out[0][0], out[-1][1] - out[0][1]) > 1e-9:
            out.append(out[0])
        return out
    holes = []
    slit_lines = []
    single = SLIT_SINGLE_LINE >= 0.5
    sacrifice = SACRIFICE_STRIP_WIDTH > 0
    if not sacrifice:
        loop = list(top_path) + curve(n_slits).tolist()        # ONE closed loop: down the right end, then along the free edge
        ang = np.linspace(0, math.pi, 28)
        for j in range(n_slits - 1, -1, -1):
            cx = (j + 0.5) * strand
            loop += [[cx + r_end * math.cos(a_), y_e + r_end * math.sin(a_)] for a_ in ang]       # round tip of strand j
            c = curve(j)
            if not single:
                loop += (c[::-1].tolist() + c.tolist()) if j > 0 else c[::-1].tolist()              # each slit up and back down (doubled); the left end only up
            elif j == 0:
                loop += c[::-1].tolist()                                                            # single-line slits: only the left end of the first strand goes up here
        loop = dedupe(loop)
    else:
        # A sacrificial strip across the free ends: each strand tip is joined to it by a small bridge. The outline is then the
        # outside of everything (allowance edge, ends, strip) plus one closed loop per gap between two neighbouring bridges
        # (it includes the doubled slit between those two strands), so no loose slit lines are left for the laser.
        cw, gap, sw = SACRIFICE_CONNECTOR_WIDTH, SACRIFICE_CONNECTOR_LENGTH, SACRIFICE_STRIP_WIDTH
        if cw <= 0 or gap <= 0:
            raise SystemExit("The sacrificial strip's bridges need a width and a length above zero (or set the strip width to 0 for no strip).")
        if cw > 0.9 * strand:
            raise SystemExit("The bridges must be narrower than a fringe strand (about 90% of its width at most).")
        d = cw / 2
        y_c = y_e + math.sqrt(r_end ** 2 - d ** 2)          # where a bridge's side meets the round tip
        y_s = W + gap                                       # top of the strip
        y_b = y_s + sw                                      # bottom of the strip
        a_r = math.acos(d / r_end)                          # tip arc angle at the right side of a bridge (the left side is pi - a_r)
        cxs = [(j + 0.5) * strand for j in range(n_slits)]

        def tip_arc(j, a0, a1, m=10):
            return [[cxs[j] + r_end * math.cos(a_), y_e + r_end * math.sin(a_)] for a_ in np.linspace(a0, a1, m)]
        loop = list(top_path) + curve(n_slits).tolist()                                           # down the right end of the last strand
        j = n_slits - 1
        loop += tip_arc(j, 0.0, a_r) + [[cxs[j] + d, y_c], [cxs[j] + d, y_s]]                   # its tip, then down its bridge
        loop += [[Lf, y_s], [Lf, y_b], [0.0, y_b], [0.0, y_s]]                                   # along the strip: right end, bottom, left end
        loop += [[cxs[0] - d, y_s], [cxs[0] - d, y_c]] + tip_arc(0, math.pi - a_r, math.pi)       # up the first strand's bridge and round its tip
        loop += curve(0)[::-1].tolist()                                                           # up the left end of the first strand
        loop = dedupe(loop)
        for j in range(n_slits - 1):                                                              # the gap between strand j and j + 1
            hp = [[cxs[j] + d, y_s], [cxs[j] + d, y_c]] + tip_arc(j, a_r, 0.0)                    # up bridge j, along tip j to the point where the strands meet
            if not single:
                hp += curve(j + 1)[::-1].tolist() + curve(j + 1).tolist()                          # the slit between them, up and back down
            hp += tip_arc(j + 1, math.pi, math.pi - a_r) + [[cxs[j + 1] - d, y_c], [cxs[j + 1] - d, y_s]]
            holes.append(dedupe(hp))
    if single:                                                                                       # each slit is one open line, from where the strands meet up to the solid part
        slit_lines = [curve(k)[::-1].tolist() for k in range(1, n_slits)]
    slit_len = sum(float(np.hypot(*np.diff(np.array(l), axis=0).T).sum()) for l in slit_lines) if single else \
        2 * sum(float(np.hypot(*np.diff(curve(k), axis=0).T).sum()) for k in range(1, n_slits))
    frill = Piece("frill")
    frill.add("cut", np.array(loop) + shift)
    for hp in holes:
        frill.add("cut", np.array(hp) + shift)
    for sl in slit_lines:
        frill.add("cut", np.array(sl) + shift)                                                       # single-line slits (open lines)
    frill.add("sew", np.array([[0, SEAM], [Lf, SEAM]]) + shift)
    if FRILL_BAND > 0:
        frill.add("mark", np.array([[0, y_fringe], [Lf, y_fringe]]) + shift)
    for p, txt in flabs:
        frill.add("label", [p + shift], txt)
    pieces.append(frill)
    # --- numbers and checks
    cones = []
    for F, nm, cut, outline in parts:
        xs, ys = np.array(outline.minimum_rotated_rectangle.exterior.coords).T
        sd = sorted([math.hypot(xs[1] - xs[0], ys[1] - ys[0]), math.hypot(xs[2] - xs[1], ys[2] - ys[1])])
        cb = cut.bounds
        if hourglass:
            sag = sag_b = 0.0
            cones.append(dict(name=nm, bbox=(cb[2] - cb[0], cb[3] - cb[1]), tight=sd[0] + 2 * SEAM, hourglass=True))
        else:
            sag = 0.0 if F.cyl else float(np.ptp(np.array([F.ring_point("a", f) for f in np.linspace(0, 1, 200)])[:, 1]))
            sag_b = 0.0 if F.cyl else float(np.ptp(np.array([F.ring_point("b", f) for f in np.linspace(0, 1, 200)])[:, 1]))
            cones.append(dict(name=nm, r_a=F.r_a, r_b=F.r_b, h=F.h, L=F.L, theta=0.0 if F.cyl else math.degrees(F.theta), cyl=F.cyl,
                              bbox=(cb[2] - cb[0], cb[3] - cb[1]), tight=sd[0] + 2 * SEAM, sag_a=sag, sag_b=sag_b))
        if sd[0] + 2 * SEAM > FABRIC_WIDTH:
            warn.append(f"The {nm} piece is {sd[0] + 2 * SEAM:.0f} mm across (tightest fit) and does not fit the {FABRIC_WIDTH:.0f} mm fabric.")
    if abs(Lf - circ_top) / circ_top > 0.02:
        pct = (Lf / circ_top - 1) * 100
        warn.append(f"The frill is {abs(pct):.0f}% {'longer' if pct > 0 else 'shorter'} than the ring it goes round "
                    f"({circ_top:.0f} mm). " + ("It will gather a little." if pct > 0 else "It will leave a gap."))
    if FRILL_NOTCH_DEPTH > SEAM - 1.5 and FRILL_NOTCH_DEPTH > 0:
        warn.append(f"Frill notch depth was cut back to {fdepth:g} mm so at least 1.5 mm of the allowance stays solid.")
    items_l, lw, lh = export_items(pieces, False)                    # nests the pieces for the laser (cached for the exports)
    ext_w, ext_h = lw - 20.0, lh - 20.0                              # the drawing itself, without the 10 mm page margin
    fits_bed = (ext_w <= LASER_BED_LONG - 10 and ext_h <= LASER_BED_SHORT - 10) or (ext_w <= LASER_BED_SHORT - 10 and ext_h <= LASER_BED_LONG - 10)
    if not fits_bed:
        warn.append(f"The nested pieces need {ext_w:.0f} x {ext_h:.0f} mm but the laser bed is {LASER_BED_SHORT:g} x {LASER_BED_LONG:g} mm (with 5 mm kept free at the edges): "
                    "they will not fit in one go. Use a smaller tube, or cut the pieces in two batches.")
    info = dict(method=1 if hourglass else 0, hg_edge=(HG.L if hourglass else 0.0), hg_centre=(HG.S_centre if hourglass else 0.0), hg_overlap=(HG.overlap if hourglass else 0.0), slit_len=slit_len, slit_single=single, n_air=n_air, n_guide=n_guide, guide_len=T.rm + GUIDE_TAB_EXTRA, laser_extent=(ext_w, ext_h), fits_bed=fits_bed, pieces=len(pieces), tube_s=T.S, cones=cones, circ_top=circ_top, circ_bottom=math.pi * DIAMETER_BOTTOM, circ_mid=circ_mid,
                frill_len=Lf, frill_w=W, F=W - y_fringe, n_slits=n_slits, strand=strand,
                n_tube_notches=n_tube_notches, n_frill_notches=n_fn, notch_w=notch_w, side_tabs=(side_lo, side_up), ring_tabs=n_ring, mid_tabs=n_mid,
                cap_d=2 * (R_top + SEAM), warnings=warn)
    return T, None, None, pieces, info


def report(info):
    L = ["SEA ANEMONE POLYP: flat pattern numbers (millimetres)", "", "Settings:"]
    L += [f"  {k:<20} {v:g}" for k, v in settings().items()]
    hg = info["method"] == 1
    L += ["", "Results:",
          (f"  Tube                            {HEIGHT:g} mm tall: TWO HOURGLASS HALVES (cut 2, two vertical seams), {DIAMETER_BOTTOM:g} mm across at the bottom, {MID_DIAMETER:g} mm at the neck "
           f"({MID_HEIGHT:g} mm up), {DIAMETER_TOP:g} mm at the top. Not exact: see below") if hg else
          (f"  Tube                            {HEIGHT:g} mm tall: two stacked cones, {DIAMETER_BOTTOM:g} mm across at the bottom, {MID_DIAMETER:g} mm at the central point "
           f"({MID_HEIGHT:g} mm up), {DIAMETER_TOP:g} mm at the top. Every piece flattens exactly (no stretch)")]
    for c in info["cones"]:
        if c.get("hourglass"):
            L.append(f"  {c['name'].capitalize():<31} half the circumference wide at every height; cut size {c['bbox'][0]:.0f} x {c['bbox'][1]:.0f} mm")
            continue
        shape = ("a plain rectangle (a cylinder)" if c["cyl"] else f"a ring sector of {c['theta']:.1f} degrees; arcs {c['sag_a']:.0f} mm and {c['sag_b']:.0f} mm deep")
        L.append(f"  {c['name'].capitalize() + ' cone':<31} {c['r_a'] * 2:.0f} to {c['r_b'] * 2:.0f} mm across over {c['h']:g} mm; straight seam {c['L']:.0f} mm; "
                 f"{shape}; cut size {c['bbox'][0]:.0f} x {c['bbox'][1]:.0f} mm")
    if hg:
        L.append(f"  Hourglass neck                  each half is the half of the lower cone joined to the half of the upper cone at the middle of the neck; the two neck arcs curve opposite ways so they overlap "
                 f"{info['hg_overlap']:.0f} mm at the sides. The seam edge is {info['hg_edge']:.0f} mm long against {info['hg_centre']:.0f} mm up the middle of the half "
                 f"({(info['hg_edge'] / info['hg_centre'] - 1) * 100:+.1f}%): expect bunching round the neck")
    L += [f"  Circumference                   bottom {info['circ_bottom']:.0f}, centre {info['circ_mid']:.0f}, top {info['circ_top']:.0f} mm",
          f"  Cap disk                        {info['cap_d']:.0f} mm across with allowance ({DIAMETER_TOP:g} mm sew circle)"
          + (f"; {CAP_HOLE_DIAMETER:g} mm centre hole for the string" if CAP_HOLE_DIAMETER > 0 else ""),
          (f"  Air holes                       {info['n_air']} holes {AIR_HOLE_DIAMETER:g} mm across, evenly spaced, {AIR_HOLE_DISTANCE:g} mm below the top seam on the {'halves' if hg else 'upper cone'}") if info["n_air"] else "  Air holes                       none",
          ("  String guide tabs               none: the hourglass method has no seam round the neck to hold them" if hg else None) or (f"  String guide tabs               {info['n_guide']} tabs at the ring seam, shared alternately between the cones; {GUIDE_TAB_WIDTH:g} mm wide, {info['guide_len']:.0f} mm from the sew line to the "
           f"hole centre (on the axis); round end {GUIDE_RING_DIAMETER:g} mm with a {GUIDE_HOLE_DIAMETER:g} mm hole") if info["n_guide"] else "  String guide tabs               none",
          f"  Frill                           one strip {info['frill_len']:.0f} x {info['frill_w']:.0f} mm; {SEAM:g} mm seam allowance"
          + (f", {FRILL_BAND:g} mm solid band" if FRILL_BAND > 0 else "")
          + f", {info['F']:.0f} mm of fringe slit into {info['n_slits']} strands {info['strand']:.1f} mm wide",
          (f"  Fringe slits                    {info['n_slits'] - 1} slits, each cut once as a single open line (SLITS layer in the DXF); total slit cutting path {info['slit_len'] / 1000:.2f} m"
           if info["slit_single"] else f"  Fringe slits                    {info['n_slits'] - 1} slits, each walked down and back up inside closed loops (cut twice); total slit cutting path {info['slit_len'] / 1000:.2f} m"),
          (f"  Sacrificial strip               a {SACRIFICE_STRIP_WIDTH:g} mm strip joins all the strand tips through {SACRIFICE_CONNECTOR_WIDTH:g} x {SACRIFICE_CONNECTOR_LENGTH:g} mm bridges; cut it off after sewing "
           f"(the frill outline then has {info['n_slits'] - 1} extra closed loops, one per gap between strands)") if SACRIFICE_STRIP_WIDTH > 0 else "  Sacrificial strip               none",
          (f"  Frill seam notches              {info['n_frill_notches']} V notches, {FRILL_NOTCHES_BETWEEN_TABS:g} between each pair of tabs, {min(FRILL_NOTCH_DEPTH, SEAM - 1.5):g} mm deep, "
           f"{info['notch_w']:.1f} mm wide at the cut edge (width worked out from the circle)") if info["n_frill_notches"]
          else "  Frill seam notches              none",
          (f"  Tube seam notches               {info['n_tube_notches']} V notches, {TUBE_NOTCHES_BETWEEN_TABS:g} between each pair of tabs, {min(TUBE_NOTCH_DEPTH, SEAM - 2.0):g} mm deep, "
           + ("on the top edge (none on the straight seams, the open bottom edge or the cap)" if hg else "on the ring seam between the cones and the top edge (none on the straight seams, the open bottom edge or the cap)"))
          if info["n_tube_notches"] else "  Tube seam notches               none",
          (f"  Alignment tabs                  {TAB_SIZE:g} wide x {TAB_LENGTH:g} mm long (frill tabs {TAB_SIZE:g} x {FRILL_TAB_LENGTH:g} mm, long enough to fold into loops for a hoop): {info['side_tabs'][0]} on each seam edge of a half "
           f"(P1.. on the left edge, Q1.. on the right edge: sew a P edge to a Q edge of the other half), {info['ring_tabs']} capital letters round the top (tube top, cap, frill)") if hg else
          (f"  Alignment tabs                  {TAB_SIZE:g} wide x {TAB_LENGTH:g} mm long (frill tabs {TAB_SIZE:g} x {FRILL_TAB_LENGTH:g} mm, long enough to fold into loops for a hoop): {info['side_tabs'][0]} (L) and {info['side_tabs'][1]} (U) numbered pairs on the straight seams, "
           f"{info['mid_tabs']} lowercase sets on the ring seam between the cones, {info['ring_tabs']} capital sets (top of the tube, cap, frill)"),
          f"  Pieces to cut                   {info['pieces']}",
          f"  Laser sheet                     nested pieces need {info['laser_extent'][0]:.0f} x {info['laser_extent'][1]:.0f} mm; bed {LASER_BED_SHORT:g} x {LASER_BED_LONG:g} mm: "
          + ("fits" if info["fits_bed"] else "DOES NOT FIT"), ""]
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
    return {"half1": "HALF 1 (cut 1). Sew P edges to the other half's Q edges; top arc to the cap and frill",
            "half2": "HALF 2 (cut 1). Sew P edges to the other half's Q edges; top arc to the cap and frill",
            "lower": "LOWER CONE (cut 1). Sew its two straight edges together; its top arc goes to the upper cone's bottom arc",
            "upper": "UPPER CONE (cut 1). Sew its two straight edges together; its top arc goes to the cap and frill",
            "cap": "CAP DISK (cut 1)",
            "frill": "FRILL STRIP (cut 1). Sew along the blue line; the slits make the fringe" + ("; cut off the thin strip at the free ends afterwards" if SACRIFICE_STRIP_WIDTH > 0 else "")}[name]


def nest_transforms(pieces):
    """Turn and shift for each piece so they pack close together on the laser sheet (see anemone_nest.py). Cached on the pieces."""
    import anemone_nest
    key = (NEST_GAP, LASER_BED_SHORT, LASER_BED_LONG, id(pieces[0]))
    cached = getattr(pieces[0], "_nest", None)
    if cached and cached[0] == key:
        return cached[1]
    shapes = {p.name: [a for k, a, t in p.items if k == "cut"][0] for p in pieces}
    tr = anemone_nest.nest(shapes, NEST_GAP, (LASER_BED_LONG - 10.0, LASER_BED_SHORT - 10.0))
    # check the real outlines really are at least (nearly) the gap apart; if not, give up on nesting
    from shapely.geometry import Polygon as _P
    from shapely.validation import make_valid as _mv
    polys = {n: _mv(_P(anemone_nest.apply(shapes[n], tr[n]))) for n in shapes}               # the real outlines, not the grown ones
    names = list(polys)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if polys[names[i]].distance(polys[names[j]]) < min(NEST_GAP, 2.0) * 0.5 and NEST_GAP > 0:
                tr = None
    pieces[0]._nest = (key, tr)
    return tr


def export_items(pieces, detailed):
    """Everything an export file draws, at true size in mm, y pointing down, shifted so the drawing starts 10 mm in from
    the corner. detailed=False keeps only the cut lines (what the laser follows): one closed outline per piece, with the pieces
    nested close together (turned as needed); the Detailed view keeps its readable layout.
    Returns (items, width, height); items are (kind, points, text) with kind cut / sew / mark / label / title."""
    tr = None if detailed else nest_transforms(pieces)
    place = layout(pieces)
    items = []
    for p in pieces:
        dx, dy, tx, ty = place[p.name]
        for k, a, t in p.items:
            if k != "cut" and not detailed:
                continue
            if tr is not None:
                import anemone_nest
                items.append((k, anemone_nest.apply(a, tr[p.name]), t))
            else:
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
        layer = {"cut": "CUT" if (closed or k != "cut") else "SLITS", "sew": "SEW", "mark": "MARK"}[k]
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
    xmax, ymax = w, h
    if not detailed:                                                   # show the laser bed (dashed) with 5 mm kept free at its edge, turned the way the layout is longer
        bw_, bh_ = (LASER_BED_LONG, LASER_BED_SHORT) if (w - 20) >= (h - 20) else (LASER_BED_SHORT, LASER_BED_LONG)
        ax.plot([5, 5 + bw_, 5 + bw_, 5, 5], [5, 5, 5 + bh_, 5 + bh_, 5], color="#8fd18f", ls=(0, (6, 4)), lw=1.0)
        ax.text(10, 5 + bh_ - 4, f"laser bed {LASER_BED_SHORT:g} x {LASER_BED_LONG:g} mm", fontsize=8, color="#8fd18f", va="bottom")
        xmax, ymax = max(w, 10 + bw_), max(h, 10 + bh_)
    ax.set_xlim(0, xmax); ax.set_ylim(ymax, 0)
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
    anemone_3d.draw(ax, T, T.S, DIAMETER_TOP / 2, info["F"], info["strand"], info["n_slits"], FRILL_WAVE, FRILL_WAVE_LENGTH,
                    mid_frac=T.lower.L / T.S, cap_hole=CAP_HOLE_DIAMETER, hourglass=info.get("method") == 1)
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
