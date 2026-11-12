"""
Holes and cutouts for the panels. Pure geometry (numpy only), no layout code in here.

Every pentagon gets a round hole of a set diameter in the middle. Every other panel gets a cutout:
its own outline pulled in by a rim that is narrow (`rim_mid`) in the middle of each side and wide
(`rim_corner`) at the corners, with rounded corners. A panel too small for a cutout stays solid.

A panel's corners are not exactly flat, so the work is done in the panel's own best-fit plane and
every point is then lifted back onto the same fan-shaped surface that the viewer draws (the surface
made of triangles from the panel's middle to each side). The result is a closed loop of 3D points,
wound the same way as the panel (anticlockwise seen from outside).
"""
import math

import numpy as np


def panel_frame(P):
    """Middle point o, outward unit normal n, in-plane axes u, w (u x w = n) for corners P (in order)."""
    o = P.mean(0)
    # Newell normal: robust for slightly bowed panels; its sign follows the winding (outward).
    n = np.zeros(3)
    for a, b in zip(P, np.roll(P, -1, 0)):
        n += np.cross(a, b)
    n /= np.linalg.norm(n)
    u = P[0] - o
    u -= (u @ n) * n
    u /= np.linalg.norm(u)
    w = np.cross(n, u)
    return o, n, u, w


def to_2d(P, o, n, u, w):
    d = P - o
    return np.stack([d @ u, d @ w], 1), d @ n


def lift(q, c2, h):
    """Heights of 2D points q on the fan surface of a panel whose corners are c2 (2D) and h (heights).
    The fan runs from the panel's middle (height 0) to each side."""
    k = len(c2)
    ang_c = np.arctan2(c2[:, 1], c2[:, 0])
    ang_q = np.arctan2(q[:, 1], q[:, 0])
    out = np.zeros(len(q))
    for j, (x, a) in enumerate(zip(q, ang_q)):
        # the fan triangle whose corner directions straddle this point
        rel = (a - ang_c) % (2 * np.pi)
        i = int(np.argmin(rel))                       # corner just before the point (going anticlockwise)
        A, B = c2[i], c2[(i + 1) % k]
        M = np.array([[A[0], B[0]], [A[1], B[1]]])
        try:
            s, t = np.linalg.solve(M, x)
        except np.linalg.LinAlgError:
            continue
        out[j] = s * h[i] + t * h[(i + 1) % k]
    return out


def _ray_hits(poly, angles):
    """Distance from the origin along each angle to the first crossing of an open polyline."""
    d = np.stack([np.cos(angles), np.sin(angles)], 1)               # (A, 2)
    p, q = poly[:-1], poly[1:]                                      # (S, 2)
    e = q - p
    # solve  t*d = p + s*e   for t > 0, 0 <= s <= 1
    den = d[:, None, 0] * e[None, :, 1] - d[:, None, 1] * e[None, :, 0]          # (A, S)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (p[None, :, 0] * e[None, :, 1] - p[None, :, 1] * e[None, :, 0]) / den
        s = (p[None, :, 0] * d[:, None, 1] - p[None, :, 1] * d[:, None, 0]) / den
    ok = (np.abs(den) > 1e-12) & (t > 1e-9) & (s >= -1e-9) & (s <= 1 + 1e-9)
    t = np.where(ok, t, np.inf)
    return t.min(1)


def cutout_radii(c2, rim_mid, rim_corner, round_r, n_angles=360, n_curve=40, shape=2.0):
    """Radius of the cutout's edge, at n_angles directions around the middle. None if too small / odd."""
    k = len(c2)
    angles = np.linspace(0, 2 * np.pi, n_angles, endpoint=False)
    rho = np.full(n_angles, np.inf)
    for i in range(k):
        A, B = c2[i], c2[(i + 1) % k]
        e = B - A
        length = np.linalg.norm(e)
        t = e / length
        inward = np.array([-t[1], t[0]])                             # anticlockwise panel: inside is on the left
        s = np.linspace(-0.6, 1.6, n_curve)
        g = np.clip(np.abs(2 * np.clip(s, 0, 1) - 1), 0, 1) ** shape  # 0 in the middle of the side, 1 at the ends
        d = rim_mid + (rim_corner - rim_mid) * g
        curve = A[None] + s[:, None] * e[None] + d[:, None] * inward[None]
        rho = np.minimum(rho, _ray_hits(curve, angles))
    if not np.all(np.isfinite(rho)):
        return None
    # Round the corners: blur the radius around the circle, but never let the cutout grow past the
    # designed outline (so the rim never gets thinner than asked).
    sigma = max(round_r / max(rho.mean(), 1e-6), 1e-3) / (2 * np.pi / n_angles)       # in samples
    half = int(math.ceil(3 * sigma))
    kern = np.exp(-0.5 * (np.arange(-half, half + 1) / sigma) ** 2)
    kern /= kern.sum()
    padded = np.concatenate([rho[-half:], rho, rho[:half]])
    smooth = np.convolve(padded, kern, mode="valid")
    return angles, np.minimum(smooth, rho)


def make_cut(P, kind, hole_diameter, rim_mid, rim_corner, round_r, min_radius=0.5, n_hole=48, n_cut=72):
    """The loop to cut out of one panel, or None.

    P: the panel's corners (k x 3, anticlockwise from outside). kind 'hole' = round hole of
    hole_diameter; kind 'cutout' = offset outline with a thin rim mid-side.
    Returns dict(kind, loop (m x 3), rim_min) or None."""
    o, n, u, w = panel_frame(P)
    c2, h = to_2d(P, o, n, u, w)
    # Needs a panel that's convex around its middle, otherwise a ray from the middle can leave and re-enter.
    e = np.roll(c2, -1, 0) - c2
    turn = e[:, 0] * np.roll(e, -1, 0)[:, 1] - e[:, 1] * np.roll(e, -1, 0)[:, 0]
    if (turn <= 0).any():
        return None
    if kind == "hole":
        a = np.linspace(0, 2 * np.pi, n_hole, endpoint=False)
        r = np.full(n_hole, hole_diameter / 2)
    else:
        res = cutout_radii(c2, rim_mid, rim_corner, round_r)
        if res is None:
            return None
        a, r = res
        if r.min() < min_radius:
            return None
        keep = np.linspace(0, len(a), n_cut, endpoint=False).astype(int)
        a, r = a[keep], r[keep]
    q = np.stack([r * np.cos(a), r * np.sin(a)], 1)
    loop = o + q[:, :1] * u + q[:, 1:] * w + lift(q, c2, h)[:, None] * n
    # rim: the smallest distance from the cut to any side, measured in the panel's plane
    rim = _min_rim(q, c2)
    return dict(kind=kind, loop=loop, rim_min=rim)


def _min_rim(q, c2):
    best = np.inf
    for A, B in zip(c2, np.roll(c2, -1, 0)):
        e = B - A
        s = np.clip(((q - A) @ e) / (e @ e), 0, 1)
        d = np.linalg.norm(q - (A + s[:, None] * e), axis=1)
        best = min(best, d.min())
    return float(best)
