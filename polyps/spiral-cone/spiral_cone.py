"""Flat sewing pattern for the spiral-cone polyp.

What it makes (all in inches):
  1. CONE STRIP   one long curved strip of woven nylon. Wound in a spiral it becomes the cone.
                  The turns sit closer together near the tip (small pitch) than at the base.
  2. RUFFLE STRIP a plain straight strip, folded in half lengthwise, sewn into the spiral seam so
                  the fold stands out on the outside as a spiral fin.
  3. CUFF BAND    a rectangle sewn into a ring; it slides over the tube.
Outputs, in the folder given with --out:
  <name>.svg      the cut lines and sew lines at true size, for the laser (red = cut, blue = sew)
  <name>.png      a picture of the flat pieces and a 3D sketch of the finished cone
  <name>.txt      the numbers and the checks (seam lengths, fabric width, warnings)

Run:  python3 spiral_cone.py --out some-folder
Change a setting without editing the file:   CONE="LENGTH=12,BASE_DIAMETER=6" python3 spiral_cone.py ...

How the flat shape is found: a cone (even a cut-off cone) can be unrolled flat without stretching or
tearing, like a paper party hat. A seam that winds up the cone becomes a spiral curve on that flat
fan. We choose the seam's height Q at every angle theta around the cone so the gap between one turn
and the next (the pitch) goes smoothly from PITCH_BASE at the bottom to PITCH_TIP at the top. The
strip is whatever lies between one turn of the seam and the next turn above it.
"""
import argparse
import math
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon

# ----------------------------------------------------------------------------- settings (inches)
LENGTH = 10.0             # cone height along its axis, cuff not included
BASE_DIAMETER = 130 / 25.4  # 130 mm. Also the cuff diameter (slides over a 5 in = 127 mm tube)
TIP_DIAMETER = 1.0        # ASSUMED, not decided. The open top, where the string is anchored.
PITCH_BASE = 3.0          # ASSUMED. Height gained per turn of the seam at the bottom
PITCH_TIP = 2.0           # ASSUMED (was 1.2, Remy wanted it less tight). Same at the top. Smaller than the base = tighter wind at the tip
PITCH_CURVE = 1.0         # 1 = pitch changes evenly with height; >1 stays open longer then tightens late
SEAM = 0.5                # seam allowance on every edge
RUFFLE_WIDTH = 3.0        # cut width of the ruffle strip (Remy: about 3 in with 1/2 in seam allowance)
RUFFLE_FULLNESS = 1.0     # ruffle length / seam length. 1 = no gathering. ASSUMED
CUFF_HEIGHT = 2.0         # finished height of the cuff
CUFF_IN_STRIP = 1         # 1 = the cuff is the bottom of the cone strip (no cuff band, 2 pieces). 0 = separate cuff band (3 pieces)
HEM = 1.0                 # extra at the open end of the cuff for a hem
FABRIC_WIDTH = 58.0       # ASSUMED usable width of the fabric. Edit when you know yours
TICK = 5.0                # alignment notches every this many inches of seam

NAMES = ["LENGTH", "BASE_DIAMETER", "TIP_DIAMETER", "PITCH_BASE", "PITCH_TIP", "PITCH_CURVE",
         "SEAM", "RUFFLE_WIDTH", "RUFFLE_FULLNESS", "CUFF_HEIGHT", "CUFF_IN_STRIP", "HEM", "FABRIC_WIDTH", "TICK"]


def settings():
    """Current settings as a dict (so the tool page can show them)."""
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


# ----------------------------------------------------------------------------- geometry
class Cone:
    """A cone (cut off at the tip) and the spiral seam on it."""

    def __init__(self):
        self.L = LENGTH
        self.r0 = BASE_DIAMETER / 2
        self.r1 = TIP_DIAMETER / 2
        if self.r1 >= self.r0 - 1e-3:
            raise SystemExit("The tip must be narrower than the base (TIP_DIAMETER < BASE_DIAMETER).")
        if PITCH_TIP <= 0 or PITCH_BASE <= 0:
            raise SystemExit("Pitch must be above zero.")
        self.zmin = -CUFF_HEIGHT if CUFF_IN_STRIP else 0.0   # the cuff continues the cone below z = 0
        self.slant = math.hypot(self.L, self.r0 - self.r1)
        self.sing = (self.r0 - self.r1) / self.slant      # sin of the cone's half angle
        self.rho0 = self.r0 / self.sing                   # flat distance from the cone's apex to the base
        self._seam_curve()

    def radius(self, z):
        return self.r0 + (self.r1 - self.r0) * np.asarray(z) / self.L

    def pitch(self, z):
        t = np.clip(np.asarray(z) / self.L, 0, 1) ** PITCH_CURVE
        return PITCH_BASE + (PITCH_TIP - PITCH_BASE) * t

    def _seam_curve(self, dth=0.004):
        """Height Q(theta) of the seam edge: dQ/dtheta = pitch(Q)/(2 pi), with Q(0) = zmin (the bottom edge)."""
        f = lambda q: float(self.pitch(q)) / (2 * math.pi)
        th, q = [0.0], [self.zmin]
        while q[-1] < self.L and len(th) < 2_000_000:
            k1 = f(q[-1]); k2 = f(q[-1] + dth * k1 / 2); k3 = f(q[-1] + dth * k2 / 2); k4 = f(q[-1] + dth * k3)
            q.append(q[-1] + dth * (k1 + 2 * k2 + 2 * k3 + k4) / 6)
            th.append(th[-1] + dth)
        # past the top the pitch stays at its top value; below 0 it stays at its base value
        extra = int(2 * math.pi / dth) + 2
        for _ in range(extra):
            q.append(q[-1] + dth * float(self.pitch(self.L)) / (2 * math.pi)); th.append(th[-1] + dth)
        back_q = [self.zmin - (i * dth) * float(self.pitch(0)) / (2 * math.pi) for i in range(extra, 0, -1)]
        back_th = [-(i * dth) for i in range(extra, 0, -1)]
        self.th = np.array(back_th + th)
        self.q = np.array(back_q + q)
        i = np.searchsorted(self.q, self.L)
        self.theta_end = float(np.interp(self.L, self.q[i - 1:i + 1], self.th[i - 1:i + 1]))  # seam reaches the top
        j = np.searchsorted(self.q, 0.0)
        self.theta_z0 = float(np.interp(0.0, self.q[j - 1:j + 1], self.th[j - 1:j + 1]))      # seam crosses the cuff line

    def Q(self, theta):
        return np.interp(theta, self.th, self.q)

    def flat(self, theta, z):
        """Unrolled position (x, y) of the point at angle theta and height z."""
        rho = self.rho0 - np.asarray(z) * self.slant / self.L
        phi = np.asarray(theta) * self.sing
        return np.column_stack([rho * np.cos(phi), rho * np.sin(phi)])

    # --- the strip: bottom edge Q(theta), top edge Q(theta + 2 pi), clipped to 0..L
    def strip_edges(self, n=1500):
        th = np.linspace(-2 * math.pi, self.theta_end, n)
        bottom = np.clip(self.Q(th), self.zmin, self.L)
        top = np.clip(self.Q(th + 2 * math.pi), self.zmin, self.L)
        return th, bottom, top

    def strip_outline(self):
        th, zb, zt = self.strip_edges()
        b = self.flat(th, zb)
        t = self.flat(th, zt)
        return np.vstack([b, t[::-1]])

    def seam_points(self, n=1500, from_cuff=False):
        """The spiral seam itself. With from_cuff, only the part above the cuff line (where the ruffle goes)."""
        th = np.linspace(self.theta_z0 if from_cuff else 0, self.theta_end, n)
        z = self.Q(th)
        return th, z

    def seam_length(self, n=6000, from_cuff=True):
        th, z = self.seam_points(n, from_cuff)
        p = self.flat(th, z)
        return float(np.sum(np.hypot(*np.diff(p, axis=0).T)))


def arclen_ticks(path, every):
    """Points along a flat polyline every `every` inches, with the local direction."""
    d = np.hypot(*np.diff(path, axis=0).T)
    s = np.concatenate([[0], np.cumsum(d)])
    out = []
    for k, target in enumerate(np.arange(0, s[-1] - 1e-6, every), start=0):
        i = min(np.searchsorted(s, target), len(path) - 1)
        i0 = max(i - 1, 0)
        if i == i0:
            i = min(i0 + 1, len(path) - 1)
        tang = path[i] - path[i0]
        tang = tang / (np.hypot(*tang) or 1)
        out.append((k, path[i], tang))
    return out


# ----------------------------------------------------------------------------- pieces and checks
def build():
    c = Cone()
    outline = Polygon(c.strip_outline()).buffer(0)
    cut = outline.buffer(SEAM, join_style=2, mitre_limit=4)
    tb = np.linspace(-2 * math.pi, 0, 400) + c.theta_z0 if CUFF_IN_STRIP else np.linspace(-2 * math.pi, 0, 400)
    if CUFF_IN_STRIP and HEM > SEAM:          # the open end of the cuff gets a bigger hem allowance
        hem = LineString(c.flat(tb, c.zmin + 0 * tb)).buffer(HEM, cap_style=2)
        cut = cut.union(hem.difference(outline)).buffer(0)
    seam = c.seam_length()
    seam_total = c.seam_length(from_cuff=False)
    ruffle_len = seam * RUFFLE_FULLNESS + 2 * SEAM
    circ = math.pi * BASE_DIAMETER
    d_bottom = 2 * float(c.radius(c.zmin))
    cuff_w, cuff_h = circ + 2 * SEAM, CUFF_HEIGHT + SEAM + HEM
    fin = (RUFFLE_WIDTH - 2 * SEAM) / 2
    rect = outline.minimum_rotated_rectangle
    xs, ys = np.array(rect.exterior.coords).T
    sides = sorted([math.hypot(xs[1] - xs[0], ys[1] - ys[0]), math.hypot(xs[2] - xs[1], ys[2] - ys[1])])
    cb = cut.bounds
    n_turns = c.theta_end / (2 * math.pi)
    strip_area = outline.area
    warn = []
    if sides[0] + 2 * SEAM > FABRIC_WIDTH:
        warn.append(f"The cone strip is {sides[0] + 2 * SEAM:.1f} in across (tightest fit) and does not fit the "
                    f"{FABRIC_WIDTH:.0f} in fabric.")
    tip_r = c.r1
    if fin > tip_r:
        warn.append(f"Fin height {fin:.2f} in is taller than the tip radius {tip_r:.2f} in. "
                    "The fins from opposite sides of the tip will crowd each other.")
    if fin > PITCH_TIP * 0.9:
        warn.append(f"Fin height {fin:.2f} in is about as tall as the tightest pitch ({PITCH_TIP:.2f} in), "
                    "so neighbouring turns of fin will press on each other near the tip.")
    if CUFF_IN_STRIP and d_bottom - BASE_DIAMETER > 0.25:
        warn.append(f"Cuff is part of the cone, so it is not a straight tube: {BASE_DIAMETER:.2f} in across at the top of the "
                    f"cuff (the tube fit) and {d_bottom:.2f} in at the open end. Use a separate cuff band (CUFF_IN_STRIP = 0) "
                    "for a straight cuff.")
    gain = lambda z: float(c.Q(np.interp(z, c.q, c.th) + 2 * math.pi) - c.Q(np.interp(z, c.q, c.th)))
    info = dict(pieces=2 if CUFF_IN_STRIP else 3, seam_total=seam_total, d_bottom=d_bottom, gain_base=gain(0.0), gain_tip=float(c.Q(c.theta_end) - c.Q(c.theta_end - 2 * math.pi)), turns=n_turns, seam=seam, ruffle_len=ruffle_len, ruffle_w=RUFFLE_WIDTH, fin=fin,
                cuff_w=cuff_w, cuff_h=cuff_h, circ=circ, strip_tight=sides[0] + 2 * SEAM,
                strip_long=sides[1] + 2 * SEAM, bbox=(cb[2] - cb[0], cb[3] - cb[1]),
                area=cut.area, half_angle=math.degrees(math.asin(c.sing)),
                tip_circ=math.pi * TIP_DIAMETER, warnings=warn)
    return c, outline, cut, info


def report(info):
    s = settings()
    lines = ["SPIRAL-CONE POLYP: flat pattern numbers (inches; 1 in = 25.4 mm)", "", "Settings:"]
    lines += [f"  {k:<16} {v:g}" for k, v in s.items()]
    lines += ["", "Results:",
              f"  Cone half-angle                 {info['half_angle']:.1f} deg",
              f"  Turns of the spiral seam        {info['turns']:.2f}",
              f"  Height gained per full turn     {info['gain_base']:.2f} in at the base, {info['gain_tip']:.2f} in at the tip "
              f"(a bit under the PITCH settings, which are the rate at that exact height)",
              f"  Seam length (sewn once)         {info['seam']:.1f} in above the cuff line (ruffle goes here)"
              + (f", {info['seam_total']:.1f} in in all with the cuff part" if CUFF_IN_STRIP else ""),
              f"  Cone strip, cut size            bounding box {info['bbox'][0]:.1f} x {info['bbox'][1]:.1f} in, "
              f"tightest rectangle {info['strip_tight']:.1f} x {info['strip_long']:.1f} in",
              f"  Ruffle strip                    {info['ruffle_w']:.1f} x {info['ruffle_len']:.1f} in, cut 1; "
              f"fin stands out {info['fin']:.2f} in (folded in half, 1/2 in allowance)",
              (f"  Cuff                            part of the cone strip: {BASE_DIAMETER:.2f} in across at the top of the cuff, "
               f"{info['d_bottom']:.2f} in at the open end, {CUFF_HEIGHT:g} in tall" if CUFF_IN_STRIP else
               f"  Cuff band                       {info['cuff_w']:.1f} x {info['cuff_h']:.1f} in, cut 1 "
               f"(ring {info['circ']:.1f} in around)"),
              f"  Tip opening, circumference      {info['tip_circ']:.1f} in",
              f"  Pieces to cut                   {info['pieces']}", ""]
    lines += ["Checks:"] + (["  " + w for w in info["warnings"]] or ["  none"])
    return "\n".join(lines)


# ----------------------------------------------------------------------------- drawing
def layout(c, cut):
    """Position of each piece on the sheet: name -> (dx, dy). Pieces are laid out one under another."""
    b = cut.bounds
    place = {"cone": (-b[0] + 1, -b[1] + 1)}
    y = (b[3] - b[1]) + 3
    place["ruffle"] = (1, y)
    y += RUFFLE_WIDTH + 2
    if not CUFF_IN_STRIP:
        place["cuff"] = (1, y)
    return place


def pieces(c, outline, cut, info):
    """Every drawn item as (piece, kind, Nx2 array in the piece's own coordinates)."""
    items = []
    items.append(("cone", "cut", np.array(cut.exterior.coords)))
    items.append(("cone", "sew", np.array(outline.exterior.coords)))
    th = np.linspace(c.theta_z0, c.theta_end, 1200)      # ticks count from the cuff line, where the ruffle starts
    if CUFF_IN_STRIP:
        tc = np.linspace(c.theta_z0 - 2 * math.pi, c.theta_z0, 300)
        items.append(("cone", "mark", c.flat(tc, 0 * tc)))   # the cuff line (top of the cuff)
    seam_path = c.flat(th, c.Q(th))
    top_path = c.flat(th - 2 * math.pi, c.Q(th))              # same seam seen from the turn above
    for k, p, tg in arclen_ticks(seam_path, TICK):
        nrm = np.array([-tg[1], tg[0]])
        items.append(("cone", "tick", np.array([p - nrm * 0.0, p + nrm * 0.45]), k))
    for k, p, tg in arclen_ticks(top_path, TICK):
        nrm = np.array([-tg[1], tg[0]])
        items.append(("cone", "tick", np.array([p, p - nrm * 0.45]), k))
    L, W = info["ruffle_len"], RUFFLE_WIDTH
    items.append(("ruffle", "cut", np.array([[0, 0], [L, 0], [L, W], [0, W], [0, 0]])))
    items.append(("ruffle", "sew", np.array([[SEAM, SEAM], [L - SEAM, SEAM], [L - SEAM, W - SEAM], [SEAM, W - SEAM], [SEAM, SEAM]])))
    items.append(("ruffle", "fold", np.array([[0, W / 2], [L, W / 2]])))
    for k in range(int(info["seam"] // TICK) + 1):               # notch k sits TICK inches of seam from the start
        x = SEAM + k * TICK * RUFFLE_FULLNESS
        for y0, y1 in ((0, 0.45), (W, W - 0.45)):
            items.append(("ruffle", "tick", np.array([[x, y0], [x, y1]]), k))
    cw, ch = info["cuff_w"], info["cuff_h"]
    if CUFF_IN_STRIP:
        return items
    items.append(("cuff", "cut", np.array([[0, 0], [cw, 0], [cw, ch], [0, ch], [0, 0]])))
    items.append(("cuff", "sew", np.array([[SEAM, HEM], [cw - SEAM, HEM], [cw - SEAM, ch - SEAM], [SEAM, ch - SEAM], [SEAM, HEM]])))
    return items


def write_svg(path, c, outline, cut, info):
    place = layout(c, cut)
    items = pieces(c, outline, cut, info)
    xs, ys = [], []
    for it in items:
        dx, dy = place[it[0]]
        xs += list(it[2][:, 0] + dx); ys += list(it[2][:, 1] + dy)
    x1, y1 = max(xs) + 1, max(ys) + 4
    style = {"cut": 'stroke="#d00000" stroke-width="0.02" fill="none"',
             "sew": 'stroke="#1d4ed8" stroke-width="0.015" stroke-dasharray="0.12 0.08" fill="none"',
             "fold": 'stroke="#15803d" stroke-width="0.015" stroke-dasharray="0.3 0.1" fill="none"',
             "tick": 'stroke="#d00000" stroke-width="0.02" fill="none"',
             "mark": 'stroke="#777" stroke-width="0.015" stroke-dasharray="0.05 0.12" fill="none"'}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1}in" height="{y1}in" viewBox="0 0 {x1:.3f} {y1:.3f}">',
           '<!-- Units are inches. Red = cut, blue dashed = sew line, green dashed = fold. -->']
    for it in items:
        dx, dy = place[it[0]]
        pts = " ".join(f"{x + dx:.4f},{y + dy:.4f}" for x, y in it[2])
        out.append(f'<polyline points="{pts}" {style[it[1]]}/>')
    ty = y1 - 2.5
    out.append(f'<rect x="1" y="{ty:.2f}" width="1" height="1" fill="none" stroke="#000" stroke-width="0.02"/>')
    out.append(f'<text x="2.2" y="{ty + 0.6:.2f}" font-size="0.3" font-family="sans-serif">1 in test square. '
               f'Cut 1 cone strip, 1 ruffle strip' + ('' if CUFF_IN_STRIP else ', 1 cuff band') + '. Notch 0 is where the ruffle starts (the cuff line); numbers match along the seam.</text>')
    for name, label in (("cone", "CONE STRIP" + (" (cuff = grey dotted line to the open end)" if CUFF_IN_STRIP else "")), ("ruffle", "RUFFLE STRIP (fold along green line)"), ("cuff", "CUFF BAND")):
        if name not in place:
            continue
        dx, dy = place[name]
        base = {"cone": (cut.bounds[0], cut.bounds[1]), "ruffle": (0, 0), "cuff": (0, 0)}[name]
        out.append(f'<text x="{base[0] + dx + 0.2:.2f}" y="{base[1] + dy + 0.5:.2f}" font-size="0.4" '
                   f'font-family="sans-serif" fill="#555">{label}</text>')
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))


def draw_png(path, c, outline, cut, info):
    fig = plt.figure(figsize=(15, 9))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[2.2, 1])
    ax = fig.add_subplot(gs[0, 0])
    items = pieces(c, outline, cut, info)
    col = {"cut": ("#d00000", "-", 1.3), "sew": ("#1d4ed8", "--", 0.9), "tick": ("#d00000", "-", 1.3), "mark": ("#777", ":", 1.0)}
    cone = [i for i in items if i[0] == "cone"]
    ax.fill(*np.array(outline.exterior.coords).T, color="#dbe7f5", zorder=0)
    for it in cone:
        k = it[1]
        ax.plot(*it[2].T, color=col[k][0], ls=col[k][1], lw=col[k][2])
        if k == "tick":
            ax.text(*(it[2][1] + (it[2][1] - it[2][0]) * 0.5), str(it[3]), fontsize=7, ha="center", va="center", color="#d00000")
    ax.set_aspect("equal"); ax.set_title("Cone strip, flat (cut 1). Red = cut, blue = sew. Numbered notches match along the seam", fontsize=10)
    ax.set_xlabel("in"); ax.grid(alpha=.25)
    # ruffle and cuff, to scale relative to each other
    ax2 = fig.add_subplot(gs[1, 0])
    L, W = info["ruffle_len"], RUFFLE_WIDTH
    for it in (i for i in items if i[0] == "ruffle"):
        k = it[1]
        if k == "fold":
            ax2.plot(*it[2].T, color="#15803d", ls="--", lw=1)
        elif k == "tick":
            ax2.plot(*it[2].T, color="#d00000", lw=1.3)
            ax2.text(it[2][0][0], it[2][0][1] + (-0.5 if it[2][0][1] == 0 else 0.5), str(it[3]), fontsize=6, ha="center")
        else:
            ax2.plot(*it[2].T, color=col[k][0], ls=col[k][1], lw=col[k][2])
    ox = L + 3
    for it in (i for i in items if i[0] == "cuff" and not CUFF_IN_STRIP):
        k = it[1]
        ax2.plot(it[2][:, 0] + ox, it[2][:, 1] + W / 2 - info["cuff_h"] / 2, color=col[k][0], ls=col[k][1], lw=col[k][2])
    ax2.text(L / 2, W + 0.8, f"Ruffle strip {W:.1f} x {L:.1f} in (fold on green line)", ha="center", fontsize=9)
    if not CUFF_IN_STRIP:
        ax2.text(ox + info["cuff_w"] / 2, W / 2 + info["cuff_h"] / 2 + 0.8, f"Cuff band {info['cuff_w']:.1f} x {info['cuff_h']:.1f} in", ha="center", fontsize=9)
    ax2.set_aspect("equal"); ax2.set_xlabel("in"); ax2.grid(alpha=.25); ax2.set_ylim(-1, W + 2.5)
    # 3D sketch
    a3 = fig.add_subplot(gs[:, 1], projection="3d")
    zz = np.linspace(c.zmin, c.L, 40); tt = np.linspace(0, 2 * math.pi, 60)
    Z, T = np.meshgrid(zz, tt)
    R = c.radius(Z)
    a3.plot_surface(R * np.cos(T), R * np.sin(T), Z, color="#dbe7f5", alpha=0.45, linewidth=0, shade=True)
    th = np.linspace(0, c.theta_end, 900)
    z = c.Q(th); r = c.radius(z)
    a3.plot(r * np.cos(th), r * np.sin(th), z, color="#1d4ed8", lw=1.2)
    for tk in th[::14]:
        if float(c.Q(tk)) < 0:
            continue                      # no ruffle on the cuff
        zk = float(c.Q(tk)); rk = float(c.radius(zk))
        fin = info["fin"]
        a3.plot([rk * math.cos(tk), (rk + fin) * math.cos(tk)], [rk * math.sin(tk), (rk + fin) * math.sin(tk)], [zk, zk], color="#c4492f", lw=1.0)
    a3.plot(*(c.r0 * np.array([np.cos(tt), np.sin(tt)])), np.zeros_like(tt) - 0, color="k", lw=1)
    if not CUFF_IN_STRIP:
        a3.plot(c.r0 * np.cos(tt), c.r0 * np.sin(tt), -CUFF_HEIGHT * np.ones_like(tt), color="#555", lw=1, ls=":")
    m = max(c.L, 2 * float(c.radius(c.zmin)) + 2 * info["fin"]) / 2
    a3.set_xlim(-m, m); a3.set_ylim(-m, m); a3.set_zlim(-CUFF_HEIGHT, c.L)
    a3.set_box_aspect((1, 1, (c.L + CUFF_HEIGHT) / (2 * m)))
    a3.view_init(18, -60)
    a3.set_title(f"Finished cone: {info['turns']:.1f} turns, pitch {PITCH_BASE:g} in at the base to {PITCH_TIP:g} in at the tip.\n"
                 "Blue = seam, red ticks = ruffle fins (not to scale of fabric folds)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def make(out, name="spiral-cone"):
    os.makedirs(out, exist_ok=True)
    c, outline, cut, info = build()
    write_svg(os.path.join(out, name + ".svg"), c, outline, cut, info)
    draw_png(os.path.join(out, name + ".png"), c, outline, cut, info)
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
