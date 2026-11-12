"""Sewing pattern for a fabric coral polyp: six fingers around a round cuff that
slides over the end of a 5 in tube.

Each finger is two mirror-image halves, so the seam runs from the centre of the top,
out over the fingertip and down the cuff. One piece, cut 12 (6 pairs).

Run:  python3 make_pattern.py          (add --no-sim to skip the 3D simulation)
Makes: pattern.pdf (print at 100 %), pattern-preview.png, polyp.png

All sizes are in inches. Change the numbers in SETTINGS and run again.
"""
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import LineString, Polygon
from shapely.ops import substring

# ---------------- SETTINGS ----------------
TUBE_DIAMETER = 5.0     # the tube the polyp slides over
EASE = 0.5              # extra room around the tube so it slides on (woven fabric)
FINGERS = 5             # number of fingers
CUFF_HEIGHT = 3.0       # finished height of the round "wrist" part
FINGER_LENGTH = 8.5     # length of a finger on the flat piece, crotch to tip
BODY_WIDTH = 2.6        # flat width of the finger's middle (it starts wider at the crotch)
TIP_WIDTH = 3.59        # flat width of the end of the finger
TIP_LENGTH = 2.06       # length of the rounded end
TIP_POINT = 0.5         # end shape: 0.5 = round, 1.0 = pointed, in between = rounded point
TAPER = 1               # 1 = ignore the body/tip widths above: the finger starts at full crotch
                        #     width and tapers all the way to a sharp point (the default design).
                        # 0 = use BODY_WIDTH / TIP_WIDTH / TIP_LENGTH / TIP_POINT (club-shaped end)
TAPER_FULLNESS = 0.6    # with TAPER: 0 = straight cone sides, higher = fuller before the point
SPLAY = 45              # degrees the fingers lean out just above the crotch
TURN_LENGTH = 1.5       # distance above the crotch over which they turn outward;
                        # above that they curve gently back to vertical at the tip
SEAM = 3 / 8            # seam allowance on every sewn edge
HEM = 1.0               # extra at the wrist edge, folded up for a hem
TUNNEL = 1              # string guides on the inner seam, tip to centre:
                        #   1 = a few short tabs (the default design, polyp-5-taper-tabs)
                        #   2 = one wider allowance along the whole seam (the earlier polyp-5-taper-string)
                        #   0 = none, plain seams (polyp-5-taper)
TUNNEL_WIDTH = 0.25     # finished width of the tunnel or tab pocket: from the seam to the second stitch line.
                        # Dyneema boa-style cord is about 1 mm, so this leaves it plenty of room.
TAB_LENGTH = 0.375      # length of each tab along the seam (1/4 to 1/2 in)
TAB_COUNT = 0           # tabs per finger. 0 = automatic: one about every TAB_SPACING, never fewer than 3
TAB_SPACING = 3.0       # automatic spacing between tab centres along the finger
TAB_MARGIN = 1.0        # nearest a tab centre gets to the fingertip and to the crotch
STRING_LOOP = 1.0       # length of cord left sticking out of the centre point for the tied loop
SCALE = 1.0             # scale model: every length above is multiplied by this (0.64 = a polyp 64 % as big)
FIT_LETTER = 0          # 1 = pick SCALE automatically so the cut piece fits on ONE 8.5 x 11 in page
                        # (for quick paper prototypes). All sizes above are then the full-size ones.
# ------------------------------------------

# Any setting can be overridden from the command line, e.g.
#   POLYP="FINGER_LENGTH=8.5,TIP_POINT=1" python3 make_pattern.py --out pointy
for _kv in filter(None, os.environ.get("POLYP", "").split(",")):
    _k, _v = _kv.split("=")
    globals()[_k.strip()] = float(_v)
FINGERS = int(FINGERS)
TUNNEL = int(TUNNEL)

LETTER_LENGTH, LETTER_WIDTH = 8.4, 6.6   # room for the cut piece on a landscape letter page, in inches,
                                         # after margins and the labels at the fingertip and the centre point


def _letter_scale():
    """The scale that makes the cut piece fit on one landscape 8.5 x 11 in page. It measures the
    full-size piece by running this script once with SCALE = 1 (a second or so)."""
    import subprocess
    env = dict(os.environ, POLYP=os.environ.get("POLYP", "") + ",SCALE=1,FIT_LETTER=0")
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--measure"], env=env,
                       capture_output=True, text=True, check=True)
    width, length = map(float, r.stdout.split("measure")[-1].split())
    return min(1.0, LETTER_LENGTH / length, LETTER_WIDTH / width)


if int(FIT_LETTER):
    SCALE = _letter_scale()
for _n in ("TUBE_DIAMETER", "EASE", "CUFF_HEIGHT", "FINGER_LENGTH", "BODY_WIDTH", "TIP_WIDTH", "TIP_LENGTH",
           "TURN_LENGTH", "SEAM", "HEM", "TUNNEL_WIDTH", "TAB_LENGTH", "TAB_SPACING", "TAB_MARGIN", "STRING_LOOP"):
    globals()[_n] *= SCALE

THUMBS = FINGERS
THUMB_LENGTH = FINGER_LENGTH
TUNNEL_SEAM = TUNNEL_WIDTH + SEAM                # seam allowance on the tabs / string seam only:
                                                 # the tunnel, plus the usual margin past its stitch line
CIRC = math.pi * TUBE_DIAMETER + EASE        # finished cuff circumference
W0 = CIRC / FINGERS                          # finished width of one piece at the crotch
TRI_DEPTH = (W0 / 2) / math.tan(math.pi / FINGERS)   # crotch line to centre of the top
BODY_H = FINGER_LENGTH - TIP_LENGTH          # where the rounded end starts
NARROW = 1.5 * SCALE                         # crotch width eases to BODY_WIDTH over this length
WIDEN = 1.5 * SCALE                          # body eases out to TIP_WIDTH over this length


def _ease(t):
    """0 to 1 smoothly as t goes 0 to 1."""
    t = np.clip(t, 0, 1)
    return (1 - np.cos(np.pi * t)) / 2


def finger_half_width(s):
    """Half the flat width of the finger at distance s above the crotch."""
    s = np.asarray(s, float)
    if TAPER:
        u = np.clip(s / FINGER_LENGTH, 0, 1)
        return W0 / 2 * (1 - u) * (1 + TAPER_FULLNESS * u)
    body = (W0 + (BODY_WIDTH - W0) * _ease(s / NARROW)
            + (TIP_WIDTH - BODY_WIDTH) * _ease((s - (BODY_H - WIDEN)) / WIDEN)) / 2
    t = np.clip((s - BODY_H) / TIP_LENGTH, 0, 1)
    tip = TIP_WIDTH / 2 * np.clip(1 - t ** 2, 0, 1) ** TIP_POINT
    return np.where(s < BODY_H, body, tip)


def thumb_outline(n=240):
    """Finished (sewing) line of the finger, left base corner, up, over the tip,
    down to the right base corner. y = 0 at the crotch level."""
    u = np.linspace(0, 1, n)
    s = FINGER_LENGTH * (1 - (1 - u) ** 1.6)          # closer points near the tip
    h = finger_half_width(s)
    left = np.column_stack([-h, s])
    right = np.column_stack([h[::-1], s[::-1]])
    return np.vstack([left, right[1:]])


def _bend_angle(s):
    """3D lean of the finger centre line away from vertical (radians), at distance s.
    Turns out from 0 to SPLAY over TURN_LENGTH, then eases back to 0 (vertical) at the tip."""
    s = np.asarray(s, float)
    th = math.radians(SPLAY)
    up = th * np.sin(np.pi / 2 * np.clip(s / TURN_LENGTH, 0, 1)) ** 2
    back = th * np.cos(np.pi / 2 * np.clip((s - TURN_LENGTH) / (FINGER_LENGTH - TURN_LENGTH), 0, 1)) ** 2
    return np.where(s < TURN_LENGTH, up, back)


def bend(pts):
    """Curve the finger part of the piece (y > 0). Where the inside edge (right, the side
    facing the centre of the polyp) is longer than the outside edge, the sewn finger
    turns outward; where it is shorter, the finger turns back up.
    A half-tube bent by angle a in 3D needs the flat piece bent by 2a/pi."""
    if SPLAY == 0:
        return pts
    grid = np.linspace(0, FINGER_LENGTH, 2001)
    phi = 2 / math.pi * _bend_angle(grid)
    ds = np.diff(grid)
    tx, ty = -np.sin(phi), np.cos(phi)
    cx = np.concatenate([[0], np.cumsum((tx[1:] + tx[:-1]) / 2 * ds)])
    cy = np.concatenate([[0], np.cumsum((ty[1:] + ty[:-1]) / 2 * ds)])
    x, y = pts[:, 0], pts[:, 1]
    yy = np.clip(y, 0, FINGER_LENGTH)
    p = np.interp(yy, grid, phi)
    bx = np.interp(yy, grid, cx) + x * np.cos(p)
    by = np.interp(yy, grid, cy) + x * np.sin(p)
    return np.where((y > 0)[:, None], np.column_stack([bx, by]), pts)


def close(*parts):
    p = np.vstack(parts)
    return np.vstack([p, p[:1]])


# The piece function returns the sewing line. `extra` lengthens the cuff for the hem.
def piece_b(extra=0.0):
    """Version B half thumb. Left of the middle: a strip of cuff. Right of the
    middle: half a triangle reaching the centre. The V between them starts at the crotch."""
    return close(bend(thumb_outline()),
                 [(W0 / 2, -TRI_DEPTH), (0, 0), (0, -CUFF_HEIGHT - extra), (-W0 / 2, -CUFF_HEIGHT - extra)])


def v_slash(cut):
    """Version B: the seam allowances fill the narrow V, so the cut line stops short of
    the crotch. Returns the slash line from the bottom of the cut V up to the crotch dot."""
    inside = cut[(cut[:, 0] > 0.05) & (cut[:, 0] < W0 / 2 - 0.05) &
                 (cut[:, 1] < -0.2) & (cut[:, 1] > -CUFF_HEIGHT)]
    tip = inside[np.argmax(inside[:, 1])]
    return np.array([tip, (0, 0)])


def tunnel_path():
    """The string seam on the sewing line: from the fingertip down the inner edge (the side
    facing the centre of the polyp), then down the triangle's straight edge to its point,
    which is the centre of the top. The string runs along this seam."""
    o = bend(thumb_outline())
    tip = (len(o) + 1) // 2 - 1                      # outline goes left edge, tip, right edge
    return np.vstack([o[tip:], [(W0 / 2, -TRI_DEPTH)]])


def _tunnel_allowance_path(lead=0.4):
    """tunnel_path() with a short lead-in down the outer edge, so the wide allowance
    wraps the tip point cleanly instead of leaving a step there."""
    o = bend(thumb_outline())
    tip = (len(o) + 1) // 2 - 1
    seg = np.hypot(*np.diff(o[:tip + 1], axis=0).T)
    back = np.cumsum(seg[::-1])                       # distance back from the tip
    i = tip - int(np.searchsorted(back, lead)) - 1
    return np.vstack([o[i:tip], tunnel_path()])


def tunnel_stitch_line():
    """TUNNEL = 2: second line of stitching, TUNNEL_WIDTH outside the seam. The two seam
    allowances, sewn together here, form the tunnel between the seam and this line."""
    return np.array(LineString(tunnel_path()).offset_curve(TUNNEL_WIDTH, join_style=2, mitre_limit=3.0).coords)


def finger_seam_length():
    """Length of the string seam along the finger itself, from the tip to the crotch."""
    o = bend(thumb_outline())
    tip = (len(o) + 1) // 2 - 1
    return float(np.hypot(*np.diff(o[tip:], axis=0).T).sum())


def tab_centres():
    """Where the tabs are, as distances along the string seam from the fingertip.
    Evenly spaced along the finger, at least 3 of them."""
    lf = finger_seam_length()
    m = min(TAB_MARGIN, lf / 4)
    n = int(TAB_COUNT) if TAB_COUNT else max(3, int(round((lf - 2 * m) / TAB_SPACING)) + 1)
    return np.linspace(m, lf - m, n) if n > 1 else np.array([lf / 2])


def tab_pieces():
    """The seam stretches that carry a tab, one LineString each (sewing line)."""
    line = LineString(tunnel_path())
    return [substring(line, c - TAB_LENGTH / 2, c + TAB_LENGTH / 2) for c in tab_centres()]


def stitch_lines():
    """Second stitch lines to draw: one per tab, or the long one, or none."""
    if TUNNEL == 1:
        return [np.array(t.offset_curve(TUNNEL_WIDTH, join_style=2, mitre_limit=3.0).coords) for t in tab_pieces()]
    if TUNNEL == 2:
        return [tunnel_stitch_line()]
    return []


def cut_line(piece_fn, has_cuff):
    base = piece_fn(HEM - SEAM if has_cuff else 0.0)
    cut = Polygon(base).buffer(SEAM, join_style=2, mitre_limit=3.0)
    if TUNNEL == 2:                                  # wider allowance, on the string seam only
        wide = LineString(_tunnel_allowance_path()).buffer(TUNNEL_SEAM, cap_style=2, join_style=3,
                                                single_sided=True)
        cut = cut.union(wide.buffer(0))
    elif TUNNEL == 1:                                # a few wider tabs
        for t in tab_pieces():
            cut = cut.union(t.buffer(TUNNEL_SEAM, cap_style=2, join_style=2, mitre_limit=3.0,
                                     single_sided=True).buffer(0))
    return np.array(cut.exterior.coords)


def _rot(p):
    """Turn the piece a quarter turn so the finger points right (fits a landscape page)."""
    p = np.atleast_2d(np.asarray(p, float))
    return np.column_stack([p[:, 1], -p[:, 0]])


def draw_tunnel(ax, lines, rotated=True, fontsize=6.5):
    """Mark the string guides on a drawing: the second stitch lines (blue), the knot at the
    tip, and the point where the cord comes out at the centre. `rotated` is True on the
    printed pages (finger pointing right) and False on the plain piece picture."""
    f = _rot if rotated else np.atleast_2d
    for line in lines:
        r = f(line)
        ax.plot(r[:, 0], r[:, 1], color="tab:blue", lw=1.3 if TUNNEL == 1 else 0.9, ls=(0, (5, 2)))
    tip, end = f(tunnel_path()[[0, -1]])
    ax.plot([tip[0]], [tip[1]], marker="o", ms=5, color="tab:blue")
    ax.plot([end[0]], [end[1]], marker="o", ms=5, color="tab:blue")
    if rotated:
        ax.text(tip[0] + 0.15, tip[1] + 0.35, "knot + stitch the cord\nto the seam here",
                fontsize=fontsize, color="tab:blue", ha="left", va="bottom")
        ax.text(end[0] - 0.1, end[1] - 0.25, "cord comes out here,\ntie the loop",
                fontsize=fontsize, color="tab:blue", ha="right", va="top")
    else:
        ax.text(tip[0] + 0.3, tip[1] + 0.3, "knot + stitch\nthe cord here",
                fontsize=fontsize, color="tab:blue", ha="left", va="bottom")
        ax.text(end[0] + 0.3, end[1] - 0.1, "cord comes out\nhere, tie the loop",
                fontsize=fontsize, color="tab:blue", ha="left", va="top")


def page(pdf, sew, cut, notches, title, lines, footer, grain_x, grain_y, text_xy, slash, tunnel=None, text_below=False):
    """Landscape pages, true size. The piece is drawn turned so the finger points right.
    If it is too long for one page it is split over several, with tape lines to join them."""
    rc, rs = _rot(cut), _rot(sew)
    x0, x1 = rc[:, 0].min() - 0.2, rc[:, 0].max() + 0.2
    cy = (rc[:, 1].min() + rc[:, 1].max()) / 2 - 0.3
    usable, overlap = 10.0, 1.0                # printable width per page, and shared strip
    n = max(1, math.ceil((x1 - x0 - overlap) / (usable - overlap)))
    if n == 1:
        lefts = [(x0 + x1) / 2 - usable / 2]
    else:
        lefts = [x0 + i * (usable - overlap) for i in range(n)]
    joins = [lefts[i + 1] + overlap / 2 for i in range(n - 1)]
    for i, L in enumerate(lefts):
        fig = plt.figure(figsize=(11, 8.5))
        ax = fig.add_axes([0, 0, 1, 1])
        left, right = L - 0.5, L + usable + 0.5
        ax.set_xlim(left, right)               # axes cover the whole page, so 1 unit = 1 inch
        ax.set_ylim(cy - 4.25, cy + 4.25)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.plot(rc[:, 0], rc[:, 1], "k-", lw=1.4)
        ax.plot(rs[:, 0], rs[:, 1], "k--", lw=0.7)
        g = _rot([(grain_x, grain_y[0]), (grain_x, grain_y[1])])
        ax.annotate("", xy=g[1], xytext=g[0], arrowprops=dict(arrowstyle="<->", lw=0.8))
        ax.text(g[:, 0].mean(), g[0, 1] + 0.08, "grain", fontsize=7, ha="center")
        sl = _rot(slash)
        ax.plot(sl[:, 0], sl[:, 1], "k-", lw=1.4)
        if tunnel is not None:
            draw_tunnel(ax, tunnel)
        ax.plot([0], [0], "ko", ms=4)
        t = _rot([(0.12, -0.55)])[0]
        ax.text(t[0], t[1], "slash to dot", fontsize=6.5, ha="center", va="top")
        marks = {"<": "^", ">": "v"}
        for (x, y, mk) in notches:             # small triangles on the cut line = match points
            p = _rot([(x, y)])[0]
            ax.plot([p[0]], [p[1]], marker=marks[mk], ms=6, color="k")
        if text_below:                         # small piece: put the notes in the empty space under it
            paras = "\n".join(lines).split("\n\n")
            half = (len(paras) + 1) // 2
            ytop = rc[:, 1].min() - 0.45
            for k, chunk in enumerate((paras[:half], paras[half:])):
                ax.text(L + usable * (0.30 if k == 0 else 0.72), ytop, "\n\n".join(chunk), ha="center", va="top", fontsize=7)
        else:
            t = _rot([text_xy])[0]
            ax.text(t[0], t[1], "\n".join(lines), ha="center", va="center", fontsize=7.5)
        top = cy + 4.25
        mid = (left + right) / 2
        label = title if n == 1 else f"{title}   (page {i + 1} of {n})"
        ax.text(mid, top - 0.55, label, ha="center", fontsize=12, weight="bold")
        piece = Polygon(rc).buffer(0)
        for xj in joins:                       # keep clear of tape lines and their notes
            piece = piece.union(Polygon([(xj - 2.2, cy - 5), (xj + 2.2, cy - 5), (xj + 2.2, cy + 5), (xj - 2.2, cy + 5)]))
        bottom = cy - 4.25
        for qx, qy in [(left + 0.5, top - 1.5), (left + 0.5, bottom + 0.8),
                       (right - 1.5, bottom + 0.8), (right - 1.5, top - 1.9)]:
            if not piece.buffer(0.2).intersects(Polygon([(qx, qy), (qx + 1, qy), (qx + 1, qy + 1), (qx, qy + 1)])):
                break
        ax.add_patch(plt.Rectangle((qx, qy), 1, 1, fill=False, lw=1))
        ax.text(qx + 0.5, qy + 0.5, "1 in\ntest\nsquare", ha="center", va="center", fontsize=6.5)
        ax.text(right - 0.5, top - 0.5, "Print at 100 % / Actual size, landscape.\nCheck the square measures 1 in.",
                ha="right", va="top", fontsize=7)
        ax.text(mid, cy - 4.25 + 0.4, footer, ha="center", fontsize=7)
        # tape lines: page i's right join matches page i+1's left join
        for j, xj in enumerate(joins):
            if j not in (i - 1, i):
                continue
            ax.plot([xj, xj], [cy - 3.6, cy + 3.2], color="0.4", lw=0.8, ls=(0, (6, 3)))
            for yy in (cy - 3.0, cy, cy + 2.6):
                ax.plot([xj], [yy], marker="D", ms=5, color="0.4")
            if j == i - 1:
                txt = f"TRIM page {i + 1} on this line,\nlay it over page {i}\nso lines and diamonds match"
                ax.text(xj + 0.1, cy - 3.6, txt, fontsize=6.5, va="bottom", ha="left", color="0.3")
            else:
                txt = f"Page {i + 2} lines up here"
                ax.text(xj - 0.1, cy - 3.6, txt, fontsize=6.5, va="bottom", ha="right", color="0.3")
        pdf.savefig(fig)
        plt.close(fig)


def cut_with_slit(cut, slash):
    """The cut outline as ONE closed path that includes the slash: where the outline reaches the bottom of
    the V, the path goes up the slash to the crotch dot and comes straight back, then carries on.
    (The slit has no width, so the laser cuts that line twice, which does no harm.)"""
    ring = np.asarray(cut, float)
    if np.allclose(ring[0], ring[-1]):
        ring = ring[:-1]
    tip, dot = np.asarray(slash, float)
    i = int(np.argmin(np.hypot(*(ring - tip).T)))
    return np.vstack([ring[:i + 1], dot, ring[i], ring[i + 1:]])


DXF_GAP = 0.125         # smallest space between pieces on the laser sheet, inches (leave room for the laser)


def write_dxf(path, cut, slash, placements=None, units="mm"):
    """DXF for a laser cutter, with ONE layer, CUT (red): each piece is a single closed outline that
    includes its slash to the dot (see cut_with_slit). Nothing else is drawn (no sewing line, marks or notches).
    placements = None writes one piece with its lower left corner at the origin. Otherwise it is a list of
    (sx, sy, dx, dy): each piece is flipped by the signs (-1 mirrors, or turns it 180 degrees together) and shifted
    (dx, dy in inches, like everything in this script).
    units = "mm" (default) writes the coordinates in millimetres, which is what laser software expects: many programs
    read the numbers as millimetres whatever the file's units flag says, so inches came in 25.4 times too small.
    units = "in" writes inches."""
    import ezdxf
    k = 25.4 if units == "mm" else 1.0
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM if units == "mm" else ezdxf.units.IN
    doc.header["$MEASUREMENT"] = 1 if units == "mm" else 0
    doc.layers.add("CUT", color=1)
    msp = doc.modelspace()
    ring = cut_with_slit(cut, slash)
    if placements is None:
        placements = [(1, 1, -ring[:, 0].min(), -ring[:, 1].min())]
    for sx, sy, dx, dy in placements:
        msp.add_lwpolyline([((x * sx + dx) * k, (y * sy + dy) * k) for x, y in ring], close=True,
                           dxfattribs={"layer": "CUT"})
    doc.saveas(path)


def save_sheet_preview(path, cut, slash, placements, size, title):
    """A picture of the laser sheet (what write_dxf draws): red outlines, slit included."""
    ring = cut_with_slit(cut, slash)
    fig, ax = plt.subplots(figsize=(6.4, 6.4 * max(0.45, min(1.6, size[1] / size[0])) + 0.7))
    for sx, sy, dx, dy in placements:
        p = ring * [sx, sy] + [dx, dy]
        ax.fill(p[:, 0], p[:, 1], facecolor="#fbe3df", edgecolor="red", lw=1.0)
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, size[0] + 0.5)
    ax.set_ylim(-0.5, size[1] + 0.5)
    ax.set_xlabel("inches")
    ax.grid(alpha=0.25)
    ax.set_title(title, fontsize=10)
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_piece_preview(path, cut, slash, title):
    """A picture of the single laser piece (what the one-piece DXF draws), with its slit."""
    ring = cut_with_slit(cut, slash)
    ring = ring - ring.min(axis=0)
    fig, ax = plt.subplots(figsize=(5, 5 * ring[:, 1].max() / max(ring[:, 0].max(), 1e-9) * 0.9 + 0.8))
    ax.fill(ring[:, 0], ring[:, 1], facecolor="#fbe3df", edgecolor="red", lw=1.2)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_xlabel("inches")
    ax.set_title(title, fontsize=10)
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_dxf_files(out, name, b_cut, slash):
    """Write <name>-piece.dxf (one piece), <name>-sheet.dxf (all 2 x FINGERS pieces, nested) and a preview."""
    try:
        import ezdxf  # noqa: F401
    except ImportError:
        print("DXF skipped: the ezdxf library isn't installed (pip3 install ezdxf)")
        return
    units = sys.argv[sys.argv.index("--dxf-units") + 1] if "--dxf-units" in sys.argv else "mm"
    u = 25.4 if units == "mm" else 1.0
    write_dxf(os.path.join(out, f"{name}-piece.dxf"), b_cut, slash, units=units)
    ring = np.asarray(b_cut, float)
    save_piece_preview(os.path.join(out, f"{name}-piece-cut.png"), b_cut, slash,
                       f"One piece, {np.ptp(ring[:, 0]):.2f} x {np.ptp(ring[:, 1]):.2f} in. Red = cut, with the slit to the dot.")
    print(f"DXF: {name}-piece.dxf (one piece, {np.ptp(ring[:, 0]) * u:.{1 if units == 'mm' else 2}f} x {np.ptp(ring[:, 1]) * u:.{1 if units == 'mm' else 2}f} {units}"
          f"{' = ' + format(np.ptp(ring[:, 0]), '.2f') + ' x ' + format(np.ptp(ring[:, 1]), '.2f') + ' in' if units == 'mm' else ''}, "
          f"slit included in the outline, file units {units})")
    if "--no-sheet" in sys.argv:
        return
    import nest
    bed = None
    if "--bed" in sys.argv:
        i = sys.argv.index("--bed")
        bed = (float(sys.argv[i + 1]), float(sys.argv[i + 2]))
    r = nest.nest_pieces(b_cut, FINGERS, gap=DXF_GAP, bed=bed)
    write_dxf(os.path.join(out, f"{name}-sheet.dxf"), b_cut, slash, r["placements"], units=units)
    w, h = r["size"]
    save_sheet_preview(os.path.join(out, f"{name}-sheet.png"), b_cut, slash, r["placements"], r["size"],
                       f"{2 * FINGERS} pieces, {w:.1f} x {h:.1f} in ({100 * r['fill']:.0f} % fabric). Grain runs up the page.")
    print(f"DXF: {name}-sheet.dxf (all {2 * FINGERS} pieces nested, {w:.1f} x {h:.1f} in"
          f"{' = ' + format(w * u, '.0f') + ' x ' + format(h * u, '.0f') + ' mm' if units == 'mm' else ''}, {100 * r['fill']:.0f} % fabric, "
          f"pieces at least {r['min_gap']:.2f} in apart; grain runs along the {h:.1f} in side)")


def main():
    if "--measure" in sys.argv:                    # used by FIT_LETTER: print the cut piece size and stop
        c = cut_line(piece_b, True)
        print(f"measure {np.ptp(c[:, 0]):.4f} {np.ptp(c[:, 1]):.4f}")
        return
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else f"polyp-{FINGERS}-taper" + {0: "", 1: "-tabs", 2: "-string"}[TUNNEL] if TAPER else f"polyp-{FINGERS}-club"
    if "--name" not in sys.argv and int(FIT_LETTER):
        name += "-letter"
    elif "--name" not in sys.argv and abs(SCALE - 1) > 1e-9:
        name += f"-x{SCALE:.2f}".rstrip("0").rstrip(".")
    os.makedirs(out, exist_ok=True)
    sa = '3/8"' if abs(SEAM - 0.375) < 1e-6 else f'{SEAM:.3g}"'
    foot = (f'Solid line = cut.  Dashed line = sew.  Seam allowance {sa} included.  '
            f'Cuff circumference {CIRC:.2f}" for a {TUBE_DIAMETER:.3g}" tube ({EASE:.3g}" ease).')
    if abs(SCALE - 1) > 1e-9:
        foot += f'  SCALE MODEL: {SCALE:.0%} of full size.'
    side_notches = [(-W0 / 2 - SEAM, 0, "<"), (W0 / 2 + SEAM, 0, ">")]
    b, b_cut = piece_b(), cut_line(piece_b, True)
    slash = v_slash(b_cut)
    lines = [f"Cut {2 * FINGERS}", f"({FINGERS} pairs: fold fabric", f"in two and cut {FINGERS})", "",
             "Outer edge + tip + inner edge", "+ triangle's straight edge", "= seam to its twin",
             "", "Both sides of the V", "= seams to the", "neighbouring finger"]
    tun = stitch_lines()
    if TUNNEL == 1:
        lines += ["", f"Blue = {len(tun)} string tabs on the inner edge.", "Sew the seam, then sew each pair of",
                  f'tabs together {TUNNEL_WIDTH:.3g}" out, on the blue line.', "The cord runs through the pockets",
                  "and is free in between."]
    elif TUNNEL == 2:
        lines += ["", "Blue = string tunnel (inner edge,", "tip to centre). Sew the seam, then",
                  f'sew the two allowances together {TUNNEL_WIDTH:.3g}"', "out on the blue line. Cord runs",
                  "between them. Wider allowance."]
    if "--dxf-only" in sys.argv:                   # laser files only (the tool's "Make laser files" button)
        make_dxf_files(out, name, b_cut, slash)
        return
    with PdfPages(os.path.join(out, f"{name}-pattern.pdf")) as pdf:
        page(pdf, b, b_cut, side_notches, f"FINGER HALF  -  {name}", lines, foot, grain_x=-0.7 * SCALE,
             grain_y=(-2.6 * SCALE, -0.3 * SCALE), text_xy=tuple(bend(np.array([[0.0, 0.4 * FINGER_LENGTH]]))[0]),
             slash=slash, tunnel=tun, text_below=SCALE < 0.85)

    fig, ax = plt.subplots(figsize=(5, 7))
    ax.plot(b_cut[:, 0], b_cut[:, 1], "k-", lw=1.4)
    ax.plot(b[:, 0], b[:, 1], "k--", lw=0.7)
    ax.plot(slash[:, 0], slash[:, 1], "k-", lw=1.4)
    ax.plot([0], [0], "ko", ms=4)
    if tun:
        draw_tunnel(ax, tun, rotated=False, fontsize=7)
    ax.set_aspect("equal")
    ax.set_title(f"{name}: finger half - cut {2 * FINGERS}\nSolid = cut line, dashed = sewing line", fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_xticks(range(-4, 4)); ax.set_yticks(range(-5, 11))
    ax.set_xlabel("inches")
    fig.savefig(os.path.join(out, f"{name}-piece.png"), dpi=110, bbox_inches="tight")
    plt.close(fig)

    if "--no-sim" not in sys.argv:
        print("simulating the sewn polyp (takes a few minutes)...")
        from sim_polyp import make_preview
        make_preview(os.path.join(out, f"{name}-3d.png"), f"Simulated from the flat pattern, inflated (fingers turn out {SPLAY:g}\u00b0, then back up)")

    if abs(SCALE - 1) > 1e-9:
        print(f"scale {SCALE:.3f} " + ("(fits one 8.5 x 11 in page)" if int(FIT_LETTER) else "(scale model)"))
    if "--no-dxf" not in sys.argv:
        make_dxf_files(out, name, b_cut, slash)
    print(f"cuff circumference {CIRC:.3f}  piece width at crotch {W0:.3f}")
    if TUNNEL:
        seg = np.diff(tunnel_path(), axis=0)
        print(f"string seam {np.hypot(seg[:, 0], seg[:, 1]).sum():.2f} in on the flat, tip to centre "
              f"(+ {STRING_LOOP:g} in cord out of the centre for the loop)")
    if TUNNEL == 1:
        c = tab_centres()
        print(f"{len(c)} tabs per finger, {TAB_LENGTH:g} in long, centres {', '.join(f'{x:.1f}' for x in c)} in from the tip")
    print(f"cut size {np.ptp(b_cut[:, 0]):.2f} x {np.ptp(b_cut[:, 1]):.2f}")


if __name__ == "__main__":
    main()
