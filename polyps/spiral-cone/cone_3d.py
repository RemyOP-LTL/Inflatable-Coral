"""A picture of the finished, inflated cone worm (no motion), drawn the same way as the sea anemone picture
(white shaded fabric on a dark background). Used by spiral_cone.py for the picture under the flat pattern.

What it shows, in plain language:
  * The cone, with the radius the pattern gives at every height (non-stretch fabric), cuff included: a flared cuff when it is part
    of the strip, a straight band when it is separate.
  * The spiral seam as a darker line winding up the cone, tighter toward the tip, then running straight for the last stretch.
  * The frill: one fringe strand every FRINGE_WIDTH along the seam between where the frill starts and ends. Each strand leaves the seam
    going outward and is blown upward by air from the base: randomly spread, trending up, with the pattern's wave. Each keeps its real length.
It is a drawing, not a physics simulation.

Drawn by hand (project every little patch of fabric onto the page, sort far to near, paint) because matplotlib's own 3D mixes up what
is in front of what when surfaces and ribbons overlap (same method as the sea anemone picture).
"""
import math
import numpy as np
from matplotlib.collections import PolyCollection


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def draw(ax, c, F, strand, n_strands, wave, wave_len, s0, s1, cuff_in_strip, cuff_h, azim=-58, elev=20, seed=11):
    """c = the Cone from spiral_cone.py; F = fringe length (mm); strand = strand width; s0..s1 = seam length range the frill covers."""
    rng = np.random.default_rng(seed)
    z_lo = c.zmin if cuff_in_strip else -cuff_h
    nprof, ntheta = 200, 220
    zg = np.linspace(z_lo, c.L, nprof)
    R0 = np.where(zg >= c.zmin, c.radius(np.maximum(zg, c.zmin)), c.r0)       # separate cuff: a straight band below the cuff line
    tipz = c.L - zg
    if c.r1 <= 0:                                                                       # round off the very tip a little (an inflated point is never perfectly sharp)
        R0 = R0 * np.sqrt(np.clip(1 - np.exp(-tipz / 2.5), 0, 1))
    th = np.linspace(0, 2 * math.pi, ntheta + 1)
    P = np.stack([R0[:, None] * np.cos(th)[None, :], R0[:, None] * np.sin(th)[None, :],
                  np.repeat(zg[:, None], ntheta + 1, axis=1)], axis=-1)

    a_rad, e_rad = math.radians(azim), math.radians(elev)
    cam = np.array([math.cos(e_rad) * math.cos(a_rad), math.cos(e_rad) * math.sin(a_rad), math.sin(e_rad)])
    right = np.array([-math.sin(a_rad), math.cos(a_rad), 0.0])
    up = np.cross(cam, right)
    light = cam * 0.55 + up * 0.85 - right * 0.55
    light /= np.linalg.norm(light)

    def proj(p):
        return np.stack([p @ right, p @ up], axis=-1), p @ cam

    def shade(n, base, k=1.0):
        d = abs(float(n @ light))
        return np.clip(base * (0.5 + 0.6 * d) * k, 0, 1)

    polys, depth, colors, edges, widths = [], [], [], [], []
    body = np.array([1.0, 1.0, 1.0])
    A, B, C, D = P[:-1, :-1], P[1:, :-1], P[1:, 1:], P[:-1, 1:]
    nrm = np.cross(C - A, D - B)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-12
    cen = (A + B + C + D) / 4
    sx, _ = proj(np.stack([A, B, C, D], axis=-2))
    zc = (zg[:-1] + zg[1:]) / 2
    thc = (th[:-1] + th[1:]) / 2
    seam_th = np.where(zc <= c.Ls, np.interp(zc, c.zg, c.thg), c.theta_end)             # azimuth of the spiral seam at each height (straight above the spiral)
    for i in range(nprof - 1):
        r_i = float((R0[i] + R0[i + 1]) / 2)
        d_ang = np.abs(((thc - seam_th[i]) + math.pi) % (2 * math.pi) - math.pi)       # angular distance from the seam, 0..pi
        dth_dz = 2 * math.pi * float(np.interp(zc[i], c.zg, c.w)) if zc[i] <= c.Ls else 0.0   # how fast the seam winds at this height
        sin_a = 1.0 / math.sqrt(1.0 + (max(r_i, 1.0) * dth_dz) ** 2)                    # the seam slants: its perpendicular distance is shorter than the distance along the ring
        dist = d_ang * max(r_i, 1.0) * sin_a                                            # distance from the seam line, mm
        on_seam = zc[i] >= c.zmin
        for j in range(ntheta):
            k = 1.0
            if on_seam:
                k = 1.0 - 0.30 * math.exp(-(dist[j] / 1.1) ** 2)                        # the seam: a darker line
            if (not cuff_in_strip) and abs(zc[i]) < 1.2:
                k = min(k, 0.78)                                                        # the seam between the separate cuff and the cone
            col = shade(nrm[i, j], body, k)
            polys.append(sx[i, j])
            depth.append(float(cen[i, j] @ cam))
            colors.append(col)
            edges.append(col)
            widths.append(0.5)

    # frill: one strand per FRINGE_WIDTH along the seam, leaving it going outward and blown upward by air from the base
    n_str = max(8, min(int(n_strands), 220))
    nseg = 16
    ds = F / nseg
    lowfreq = sum(rng.normal() * np.sin(2 * math.pi * (f * np.arange(n_str) / n_str) + rng.uniform(0, 6.28)) for f in (2, 3, 5)) / 2.5
    gam = math.asin(c.sing)                                                            # the cone's own slope: the surface normal leans up by this much
    for i in range(n_str):
        s_i = s0 + (i + 0.5) * (s1 - s0) / n_str
        a_i, z_i = c.at_s(s_i)
        r_i = float(c.radius(z_i))
        rad = np.array([math.cos(a_i), math.sin(a_i), 0.0])
        th_hat = np.array([-math.sin(a_i), math.cos(a_i), 0.0])
        p = np.array([r_i * rad[0], r_i * rad[1], z_i])
        beta_max = np.clip(math.radians(46 + 16 * lowfreq[i] + 12 * rng.normal()), math.radians(14), math.radians(82))
        beta0 = gam + math.radians(4 + 6 * rng.random())
        yaw = math.radians(6 * lowfreq[i] + 5 * rng.normal())
        tw0 = math.radians(rng.uniform(-30, 30))
        pts, tans, pos = [p.copy()], [], p.copy()
        for k in range(nseg):
            u = (k + 0.5) / nseg
            beta = beta0 + (beta_max - beta0) * _smooth(u * 1.15) ** 0.8
            psi = a_i + yaw * (0.4 + u)
            t = np.array([math.cos(beta) * math.cos(psi), math.cos(beta) * math.sin(psi), math.sin(beta)])
            pos = pos + t * ds
            lat = wave * math.sin(2 * math.pi * (k + 1) * ds / max(wave_len, 5.0)) * _smooth(u * 4) * _smooth((1 - u) * 4)
            pts.append(pos + th_hat * lat)
            tans.append(t)
        pts = np.array(pts)
        tans.append(tans[-1])
        base = body * (0.84 + 0.16 * rng.random())                                     # each strand a slightly different tone so neighbours read apart
        hw = 0.5 * strand * 0.92
        wd = []
        for k in range(nseg + 1):
            t = tans[k]
            w0 = th_hat - t * float(th_hat @ t)
            w0 /= np.linalg.norm(w0) + 1e-12
            tw = tw0 * math.sin(math.pi * k / nseg * 1.3)
            wd.append(w0 * math.cos(tw) + np.cross(t, w0) * math.sin(tw))
        for k in range(nseg):
            q = np.array([pts[k] - wd[k] * hw, pts[k + 1] - wd[k + 1] * hw, pts[k + 1] + wd[k + 1] * hw, pts[k] + wd[k] * hw])
            n = np.cross(q[1] - q[0], q[3] - q[0])
            n /= np.linalg.norm(n) + 1e-12
            col = shade(n, base)
            s2, _ = proj(q)
            polys.append(s2)
            depth.append(float(q.mean(axis=0) @ cam) + 0.8)                           # strands start at the seam: nudge toward the viewer so they sit on top of it
            colors.append(col)
            edges.append(col)
            widths.append(0.4)

    order = np.argsort(depth)
    ax.add_collection(PolyCollection([polys[i] for i in order], facecolors=[colors[i] for i in order],
                                     edgecolors=[edges[i] for i in order], linewidths=[widths[i] for i in order], antialiaseds=True))
    allp = np.vstack(polys)
    pad = 0.04 * np.ptp(allp, axis=0).max()
    ax.set_xlim(allp[:, 0].min() - pad, allp[:, 0].max() + pad)
    ax.set_ylim(allp[:, 1].min() - pad, allp[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
