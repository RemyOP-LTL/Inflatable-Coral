#!/usr/bin/env python3
"""
The spine is a CURVE that comes with the surface file (Remy, 2026-11-16): the file holds the surface and a curve lying on it.
This module reads that curve and gives spine coordinates for any point on the surface:
    sigma = distance along the curve (inches), u = signed distance from the curve (inches, to one side or the other).
and the way back: (sigma, u) -> a point on the surface.

Surface files (OBJ): the curve is stored as comment lines   # spine x y z   (one per point, in inches). Other readers ignore
them. STEP files: see step_curve.py. Needs numpy and scipy.
"""
import numpy as np
from scipy.spatial import cKDTree


def read_curve(path):
    """Curve points stored in an OBJ as '# spine x y z' lines, or None."""
    pts = []
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("# spine "):
                    pts.append([float(x) for x in line.split()[2:5]])
    except (OSError, UnicodeDecodeError):
        return None
    return np.array(pts, float) if len(pts) >= 2 else None


class SpineCurve:
    """The curve, plus its continuation past both ends along its own circular arc (EXT inches), so nodes in the extra rows the layout adds past the open edges still get spine coordinates. The spine piece itself covers only the curve (the surface)."""
    EXT = 30.0

    def __init__(self, pts, surface, step=0.1):
        pts = np.asarray(pts, float)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        self.length = float(s[-1])
        n = max(2, int(self.length / step) + 1)
        s_in = np.linspace(0.0, self.length, n)
        c = surface.snap(np.stack([np.interp(s_in, s, pts[:, k]) for k in range(3)], 1))   # lie exactly on the surface
        t = np.gradient(c, axis=0)
        k = max(1, int(round(1.0 / step)))                                  # smooth the direction over about an inch
        ker = np.ones(2 * k + 1) / (2 * k + 1)
        t = np.stack([np.convolve(np.pad(t[:, i], k, mode="edge"), ker, mode="valid") for i in range(3)], 1)
        t /= np.linalg.norm(t, axis=1)[:, None]
        _, j = surface.tree.query(c)
        nr = surface.nrm[j]
        nr = nr - (nr * t).sum(1)[:, None] * t
        nr /= np.linalg.norm(nr, axis=1)[:, None]
        nr *= np.sign((nr * nr[len(nr) // 2]).sum(1))[:, None]               # one consistent side along the whole curve
        self.n_in = len(s_in)
        # continuation past each end: keep the end tangent turning at the end's curvature
        def arc(c_e, t_e, n_e, kappa_vec, ss):
            kk = float(np.linalg.norm(kappa_vec))
            if kk < 1e-6:
                return c_e + np.outer(ss, t_e), np.tile(t_e, (len(ss), 1)), np.tile(n_e, (len(ss), 1))
            m = kappa_vec / kk; th = kk * ss
            ax = np.cross(t_e, m); ax /= np.linalg.norm(ax)
            pos = c_e + np.outer(np.sin(th) / kk, t_e) + np.outer((1 - np.cos(th)) / kk, m)
            def rot(v):
                return (np.outer(np.cos(th), v) + np.outer(np.sin(th), np.cross(ax, v)) + np.outer(1 - np.cos(th), ax * np.dot(ax, v)))
            return pos, rot(t_e), rot(n_e)
        m_ = max(2, int(10.0 / step))
        ss = np.arange(step, self.EXT + 1e-9, step)
        ke = (t[-1] - t[-1 - m_]) / (m_ * step); kb = (t[m_] - t[0]) / (m_ * step)           # turning of the direction, per inch, at the end and (going backward) at the start
        pe, te, ne = arc(c[-1], t[-1], nr[-1], ke, ss)
        pb, tb, nb = arc(c[0], -t[0], nr[0], kb, ss)
        self.s = np.concatenate([-ss[::-1], s_in, self.length + ss])
        self.c = np.vstack([pb[::-1], c, pe]); self.t = np.vstack([-tb[::-1], t, te]); self.n = np.vstack([nb[::-1], nr, ne])
        self.inside = np.concatenate([np.zeros(len(ss), bool), np.ones(len(s_in), bool), np.zeros(len(ss), bool)])
        self.side = np.cross(self.n, self.t)
        self.tree = cKDTree(self.c)
        self.surface = surface

    def station(self, P):
        """(sigma, u, dist) for points P (N,3): dist is the straight-line distance to the curve; u carries the side."""
        P = np.atleast_2d(P)
        d, i = self.tree.query(P)
        sign = np.where(((P - self.c[i]) * self.side[i]).sum(1) >= 0, 1.0, -1.0)
        return self.s[i], sign * d, d

    def _snap(self, X, inside):
        out = np.array(X, float)
        if inside.any():
            out[inside] = self.surface.snap(X[inside])
        return out

    def to3d(self, sigma, u):
        """Surface point at spine coordinates (sigma, u): a point u from the curve (straight-line distance), on the surface."""
        sigma = np.clip(np.atleast_1d(sigma).astype(float), self.s[0], self.s[-1])
        i = np.clip(np.searchsorted(self.s, sigma), 0, len(self.s) - 1)
        c, side, ins = self.c[i], self.side[i], self.inside[i]
        u = np.atleast_1d(u).astype(float) * np.ones_like(sigma)
        w = u.copy()
        for _ in range(4):                                                  # make the straight-line distance come out as u
            got = np.linalg.norm(self._snap(c + side * w[:, None], ins) - c, axis=1)
            w = np.where((np.abs(u) > 1e-9) & (got > 1e-9), w * np.abs(u) / np.maximum(got, 1e-9), w)
        return self._snap(c + side * w[:, None], ins)
