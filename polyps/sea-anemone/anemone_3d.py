"""A picture of the finished, inflated sea anemone (no motion). Used by sea_anemone.py for the right-hand preview.

What it tries to show, in plain language:
  * The tube keeps the circumference of the flat pattern at every height (non-stretch fabric).
  * The top is a cap disk sewn to the tube. The seam ring is held at a fixed size, just under the top diameter setting
    (K_TOP, 96%), and does not collapse further. So the top keeps its shape and the cap only pouches into a shallow
    dome: its fabric (seam to centre) is exactly the cap radius, which fixes how high it can rise.
  * The tube wall follows the pattern's radius, eases in to the seam ring over the last 14 mm, and sits at the height
    where the tube fabric (bottom to seam) is exactly the pattern's side-edge length.
  * The ring is a little smaller than the tube top, so a little fabric gathers: small wrinkles are drawn round the seam
    (the cap edge has no notches on purpose, so it wrinkles).
  * The frill strands leave the seam going outward and are blown upward by air coming from the base: randomly spread,
    trending up. Each strand keeps its real length.
It is a drawing, not a physics simulation: the corner shape and the wind are chosen to look right.

The picture is drawn by hand (project every little patch of fabric onto the page, sort far to near, paint) because
matplotlib's own 3D mixes up what is in front of what when surfaces and ribbons overlap.
"""
import math
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb

K_TOP = 0.96         # the seam ring is held at this fraction of the top diameter setting (just smaller) and does not collapse further
TAPER = 14.0         # over the last this-many mm the tube wall eases in to the seam ring


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _arc(r, z):
    return float(np.hypot(np.diff(r), np.diff(z)).sum())


def _dome_angle(k):
    """Half-angle theta (radians) of a spherical cap whose fabric radius (arc) is 1 and whose base radius is k: sin(theta)/theta = k."""
    lo, hi = 1e-6, math.pi - 1e-3
    for _ in range(60):
        m = (lo + hi) / 2
        if math.sin(m) / m > k:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def profile(T, S_target, cap_radius):
    """The inflated outline (radius, height) of the tube and the dome, and the index of the seam point.
    The seam ring is held at K_TOP x the top radius. The cap is a shallow spherical dome whose fabric (seam to centre)
    is exactly the cap radius. The tube wall follows the pattern's radius and eases in to the seam ring; the height where
    the seam sits is solved so the tube fabric (bottom to seam) is exactly the pattern's side-edge length."""
    r_s = K_TOP * cap_radius

    def wall(zs, n=240):
        z = np.linspace(0, zs, n)
        r_pat = np.interp(z, T.z, T.r)
        r = r_pat + (r_s - r_pat) * _smooth((z - (zs - TAPER)) / TAPER)
        return r, z

    lo, hi = 0.3 * T.z[-1], 1.2 * T.z[-1]
    for _ in range(50):
        zs = (lo + hi) / 2
        rw, zw = wall(zs)
        if _arc(rw, zw) > S_target:
            hi = zs
        else:
            lo = zs
    zs = (lo + hi) / 2
    rw, zw = wall(zs)
    theta = _dome_angle(min(r_s / cap_radius, 0.9999))
    rho = cap_radius / theta                                 # sphere radius of the dome
    a = np.linspace(theta, 0, 120)
    rd = rho * np.sin(a)
    zd = zs - rho * math.cos(theta) + rho * np.cos(a)
    r = np.r_[rw, rd[1:]]
    z = np.r_[zw, zd[1:]]
    return r, z, len(rw) - 1


def draw(ax, T, S_target, cap_radius, frill_len, strand, n_strands, wave, wave_len, azim=-58, elev=22, seed=11, mid_frac=None):
    rng = np.random.default_rng(seed)
    pr, pz, i_seam = profile(T, S_target, cap_radius)
    # resample the profile evenly by arc length so the patches are even
    s = np.r_[0, np.cumsum(np.hypot(np.diff(pr), np.diff(pz)))]
    nprof = 110
    sg = np.linspace(0, s[-1], nprof)
    R0 = np.interp(sg, s, pr)
    Z0 = np.interp(sg, s, pz)
    sig = 9.0 / (sg[1] - sg[0])                      # round off the join between tube wall and corner (about 9 mm)
    kk = np.arange(-int(4 * sig), int(4 * sig) + 1)
    ker = np.exp(-0.5 * (kk / sig) ** 2)
    ker /= ker.sum()

    def blur(v):
        pad = int(4 * sig)
        vp = np.r_[np.full(pad, v[0]), v, 2 * v[-1] - v[-2::-1][:pad] if False else np.full(pad, v[-1])]
        return np.convolve(vp, ker, mode="same")[pad:-pad]
    R0 = blur(R0)
    R0[-1] = 0.0
    Z0 = blur(Z0)
    s_seam = s[i_seam]
    ntheta = 120
    th = np.linspace(0, 2 * math.pi, ntheta + 1)
    # gathers (small wrinkles) round the seam, strongest on the cap side
    s_mid = None if mid_frac is None else mid_frac * s_seam           # the ring seam between the two cones, at the same fraction of the tube fabric
    dist = (sg - s_seam)[:, None]
    env = np.exp(-(dist / 14.0) ** 2) * np.where(dist > 0, 1.0, 0.6)
    wr = (0.022 * np.sin(26 * th + 0.7) + 0.012 * np.sin(41 * th + 2.1) + 0.008 * np.sin(13 * th)) * env
    if s_mid is not None:                                              # a few small gathers along the middle seam too (both arcs have the same length, so fewer than at the cap)
        dm = (sg - s_mid)[:, None]
        wr = wr + (0.006 * np.sin(31 * th + 1.3) + 0.004 * np.sin(17 * th + 0.4)) * np.exp(-(dm / 9.0) ** 2)
    RR = R0[:, None] * (1 + wr)
    X = RR * np.cos(th)[None, :]
    Y = RR * np.sin(th)[None, :]
    Zs = np.repeat(Z0[:, None], ntheta + 1, axis=1)
    P = np.stack([X, Y, Zs], axis=-1)                                # (nprof, ntheta+1, 3)

    a_rad = math.radians(azim)
    e_rad = math.radians(elev)
    cam = np.array([math.cos(e_rad) * math.cos(a_rad), math.cos(e_rad) * math.sin(a_rad), math.sin(e_rad)])
    right = np.array([-math.sin(a_rad), math.cos(a_rad), 0.0])
    up = np.cross(cam, right)
    light = cam * 0.55 + up * 0.85 - right * 0.55
    light /= np.linalg.norm(light)

    def proj(p):
        return np.stack([p @ right, p @ up], axis=-1), p @ cam

    polys, depth, colors, edges, widths = [], [], [], [], []
    body = np.array([1.0, 1.0, 1.0])
    seamdark = 0.72

    def shade(n, base, k=1.0):
        d = abs(float(n @ light))
        return np.clip(base * (0.5 + 0.6 * d) * k, 0, 1)

    # fabric patches
    A, B, C, D = P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:]
    nrm = np.cross(C - A, D - B)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-12
    cen = (A + B + C + D) / 4
    sx, dx = proj(np.stack([A, B, C, D], axis=-2))
    sc = sg[:-1] + (sg[1] - sg[0]) / 2
    for i in range(nprof - 1):
        k = seamdark if (abs(sc[i] - s_seam) < 2.0 or (s_mid is not None and abs(sc[i] - s_mid) < 1.6)) else 1.0
        for j in range(ntheta):
            col = shade(nrm[i, j], body, k)
            polys.append(sx[i, j])
            depth.append(float((cen[i, j] @ cam)))
            colors.append(col)
            edges.append(col)
            widths.append(0.5)
    # the side seam (a darker line up the tube at angle 0)
    # (drawn by darkening the patches in the first column of the tube part)
    for i in range(0, int(np.argmin(np.abs(sg - s_seam)))):
        idx = i * ntheta
        colors[idx] = colors[idx] * 0.75
        edges[idx] = colors[idx]

    # frill strands: leave the seam ring going outward, bent upward by wind from below
    seam_r = RR[np.argmin(np.abs(sg - s_seam))]
    seam_z = float(np.interp(s_seam, sg, Z0))
    n_str = max(8, min(int(n_strands), 160))
    pal = [np.array([1.0, 1.0, 1.0])]
    nseg = 18
    ds = frill_len / nseg
    lowfreq = sum(rng.normal() * np.sin(2 * math.pi * (f * np.arange(n_str) / n_str) + rng.uniform(0, 6.28)) for f in (2, 3, 5)) / 2.5
    for i in range(n_str):
        ang = 2 * math.pi * (i + 0.5) / n_str
        th_hat = np.array([-math.sin(ang), math.cos(ang), 0.0])
        rad = np.array([math.cos(ang), math.sin(ang), 0.0])
        r_here = float(np.interp(ang % (2 * math.pi), th, seam_r))
        p = np.array([r_here * rad[0], r_here * rad[1], seam_z])
        beta_max = np.clip(math.radians(52 + 17 * lowfreq[i] + 13 * rng.normal()), math.radians(12), math.radians(84))
        beta0 = math.radians(8 + 6 * rng.random())
        yaw = math.radians(7 * lowfreq[i] + 5 * rng.normal())
        tw0 = math.radians(rng.uniform(-30, 30))
        pts, tans = [p.copy()], []
        pos = p.copy()
        for k in range(nseg):
            u = (k + 0.5) / nseg
            beta = beta0 + (beta_max - beta0) * _smooth(u * 1.15) ** 0.8
            psi = ang + yaw * (0.4 + u)
            t = np.array([math.cos(beta) * math.cos(psi), math.cos(beta) * math.sin(psi), math.sin(beta)])
            pos = pos + t * ds
            lat = wave * math.sin(2 * math.pi * (k + 1) * ds / max(wave_len, 5.0)) * _smooth(u * 4) * _smooth((1 - u) * 4)
            pts.append(pos + th_hat * lat)
            tans.append(t)
        pts = np.array(pts)
        tans.append(tans[-1])
        base = pal[0] * (0.84 + 0.16 * rng.random())          # all white; each strand a slightly different tone so neighbours read apart
        hw = 0.5 * strand * 0.92
        wd = []
        for k in range(nseg + 1):
            t = tans[k]
            w0 = th_hat - t * float(th_hat @ t)
            w0 /= np.linalg.norm(w0) + 1e-12
            tw = tw0 * math.sin(math.pi * k / nseg * 1.3)
            w = w0 * math.cos(tw) + np.cross(t, w0) * math.sin(tw)
            wd.append(w)
        for k in range(nseg):
            q = np.array([pts[k] - wd[k] * hw, pts[k + 1] - wd[k + 1] * hw, pts[k + 1] + wd[k + 1] * hw, pts[k] + wd[k] * hw])
            n = np.cross(q[1] - q[0], q[3] - q[0])
            n /= np.linalg.norm(n) + 1e-12
            col = shade(n, base)
            s2, d2 = proj(q)
            polys.append(s2)
            depth.append(float(q.mean(axis=0) @ cam) + 0.8)       # strands start at the seam: nudge toward the viewer so they sit on top of it
            colors.append(col)
            edges.append(col)
            widths.append(0.4)

    order = np.argsort(depth)
    pc = PolyCollection([polys[i] for i in order], facecolors=[colors[i] for i in order],
                        edgecolors=[edges[i] for i in order], linewidths=[widths[i] for i in order], antialiaseds=True)
    ax.add_collection(pc)
    allp = np.vstack(polys)
    pad = 0.04 * np.ptp(allp, axis=0).max()
    ax.set_xlim(allp[:, 0].min() - pad, allp[:, 0].max() + pad)
    ax.set_ylim(allp[:, 1].min() - pad, allp[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    return dict(wall_top=float(pz[i_seam]), height=float(pz.max()), seam_radius=float(np.interp(s_seam, s, pr)))
