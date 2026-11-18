"""A picture of the finished, inflated sea anemone (no motion). Used by sea_anemone.py for the right-hand preview.

What it tries to show, in plain language:
  * The tube keeps the circumference of the flat pattern at every height (non-stretch fabric).
  * The top is a cap disk sewn to the tube. Inflated, it puffs into a dome, and the sewn seam sits on the rounded
    corner between the tube wall and the dome. The shape of that corner is found so that the fabric lengths match:
    the tube fabric reaches exactly as far as the flat pattern says, and the cap fabric runs from the seam to the
    centre of the dome with exactly the cap's radius.
  * The seam ring is slightly smaller than the tube top, so a little fabric has to gather: you see small wrinkles
    round the seam (the cap edge has no notches on purpose, so it wrinkles).
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

N_EXP = 2.5          # corner roundness of the dome profile (2 = ellipse, higher = squarer corner)
PHI_SEAM = 0.5       # where on the corner the seam sits (radians along the corner curve, 0 = start of the corner)


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _arc(r, z):
    return float(np.hypot(np.diff(r), np.diff(z)).sum())


def _corner(a, z0, b, phi0, phi1, n=80):
    """Part of the dome profile: a superellipse starting vertical at the tube wall (radius a, height z0), semi-height b."""
    phi = np.linspace(phi0, phi1, n)
    e = 2.0 / N_EXP
    return a * np.cos(phi) ** e, z0 + b * np.sin(phi) ** e


def profile(T, S_target, cap_radius):
    """The inflated outline (radius, height) of tube + shoulder + dome, and the index of the seam point.
    Solves for the height z0 where the tube wall ends and the dome height b so that
    tube fabric length (bottom to seam) = S_target and cap fabric length (seam to centre) = cap_radius."""
    def wall(z0, n=200):
        z = np.linspace(0, z0, n)
        return np.interp(z, T.z, T.r), z

    def solve_b(a, z0):
        lo, hi = 0.02 * a, 3.0 * a
        for _ in range(50):
            b = (lo + hi) / 2
            r, z = _corner(a, z0, b, PHI_SEAM, math.pi / 2)
            if _arc(r, z) > cap_radius:
                hi = b
            else:
                lo = b
        return (lo + hi) / 2

    def tube_len(z0):
        a = float(np.interp(z0, T.z, T.r))
        b = solve_b(a, z0)
        rw, zw = wall(z0)
        rs, zs = _corner(a, z0, b, 0.0, PHI_SEAM)
        return _arc(np.r_[rw, rs], np.r_[zw, zs]), a, b

    lo, hi = 0.2 * T.z[-1], T.z[-1]
    for _ in range(40):
        z0 = (lo + hi) / 2
        L, a, b = tube_len(z0)
        if L > S_target:
            hi = z0
        else:
            lo = z0
    z0 = (lo + hi) / 2
    L, a, b = tube_len(z0)
    rw, zw = wall(z0)
    rc, zc = _corner(a, z0, b, 0.0, math.pi / 2, n=160)
    r = np.r_[rw, rc[1:]]
    z = np.r_[zw, zc[1:]]
    i_seam = len(rw) - 1 + int(np.argmin(np.abs(np.linspace(0, math.pi / 2, 160) - PHI_SEAM)))
    return r, z, i_seam


def draw(ax, T, S_target, cap_radius, frill_len, strand, n_strands, wave, wave_len, azim=-58, elev=22, seed=11):
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
    dist = (sg - s_seam)[:, None]
    env = np.exp(-(dist / 14.0) ** 2) * np.where(dist > 0, 1.0, 0.6)
    wr = (0.022 * np.sin(26 * th + 0.7) + 0.012 * np.sin(41 * th + 2.1) + 0.008 * np.sin(13 * th)) * env
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
        k = seamdark if abs(sc[i] - s_seam) < 2.0 else 1.0
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
