#!/usr/bin/env python3
"""
Find the spine curve in a STEP file (Remy, 2026-11-16: an uploaded STEP holds a surface and a curve on it).

Reads the text of the STEP file directly. Looks for free curves (not an edge of any face): B-spline curves (plain or rational)
and polylines. If there are several, the longest is the spine. Points come back in inches. Best effort: a curve made only of
arcs and lines is not read yet. Needs numpy and scipy.
"""
import re

import numpy as np
from scipy.interpolate import BSpline


def _entities(text):
    text = re.sub(r"\s+", " ", text)
    return {int(m.group(1)): m.group(2).strip() for m in re.finditer(r"#(\d+)\s*=\s*(.*?);(?=\s*(?:#|ENDSEC))", text)}


def _nums(s):
    return [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)]


def _ids(s):
    return [int(x) for x in re.findall(r"#(\d+)", s)]


def unit_scale(ents):
    """Inches per file length unit."""
    for e in ents.values():
        if "LENGTH_UNIT" in e and "SI_UNIT" in e:
            m = re.search(r"SI_UNIT\(\s*\.?(\w+)?\.?\s*,\s*\.METRE\.", e) or re.search(r"SI_UNIT\(\s*(\$)\s*,\s*\.METRE\.", e)
            pre = (m.group(1) or "") if m else ""
            return {"MILLI": 1 / 25.4, "CENTI": 1 / 2.54, "": 39.3700787, "$": 39.3700787, "KILO": 39370.0787}.get(pre, 1 / 25.4)
        if "CONVERSION_BASED_UNIT" in e and "INCH" in e.upper():
            return 1.0
    return 1 / 25.4


def _point(ents, i):
    m = re.search(r"CARTESIAN_POINT\('[^']*',\(([^()]*)\)\)", ents[i])
    return np.array(_nums(m.group(1))[:3]) if m else None


def _bspline(ents, i, e):
    cp_ids = _ids(re.search(r"B_SPLINE_CURVE(?:_WITH_KNOTS)?\(\s*'[^']*'\s*,\s*(\d+)\s*,\s*\(([^)]*)\)", e).group(2))
    deg = int(re.search(r"B_SPLINE_CURVE(?:_WITH_KNOTS)?\(\s*'[^']*'\s*,\s*(\d+)", e).group(1))
    kn = re.search(r"B_SPLINE_CURVE_WITH_KNOTS\((?:\s*'[^']*'\s*,\s*\d+\s*,\s*\([^)]*\)\s*,\s*\.\w+\.\s*,\s*\.\w\.\s*,\s*\.\w\.\s*,)?\s*\(([^)]*)\)\s*,\s*\(([^)]*)\)", e)
    if not kn:
        return None
    mult, knots = [int(x) for x in _nums(kn.group(1))], _nums(kn.group(2))
    t = np.repeat(knots, mult)
    P = np.array([_point(ents, k) for k in cp_ids])
    w = re.search(r"RATIONAL_B_SPLINE_CURVE\(\s*\(([^)]*)\)", e)
    if w:
        W = np.array(_nums(w.group(1)))
        H = BSpline(t, np.column_stack([P * W[:, None], W]), deg)
        u = np.linspace(t[deg], t[-deg - 1], 400)
        h = H(u)
        return h[:, :3] / h[:, 3:4]
    return BSpline(t, P, deg)(np.linspace(t[deg], t[-deg - 1], 400))


def find_curve(text):
    """(points in inches, description) of the spine curve in STEP text, or (None, why not)."""
    ents = _entities(text)
    scale = unit_scale(ents)
    curves = {}
    for i, e in ents.items():
        try:
            if "B_SPLINE_CURVE" in e and "B_SPLINE_SURFACE" not in e:
                pts = _bspline(ents, i, e)
            elif e.startswith("POLYLINE("):
                pts = np.array([_point(ents, k) for k in _ids(e)])
            else:
                continue
        except (AttributeError, KeyError, ValueError, TypeError):
            continue
        if pts is not None and len(pts) >= 2:
            curves[i] = np.asarray(pts, float) * scale
    if not curves:
        return None, "I found no curve (B-spline or polyline) in that STEP file."
    edge_curve = {}
    for i, e in ents.items():
        m = re.match(r"EDGE_CURVE\('[^']*',#\d+,#\d+,#(\d+),", e)
        if m:
            edge_curve[i] = int(m.group(1))
    used_edges = {k for e in ents.values() if e.startswith("ORIENTED_EDGE(") for k in _ids(e)}
    on_faces = {c for ed, c in edge_curve.items() if ed in used_edges}
    free = {i: p for i, p in curves.items() if i not in on_faces}
    if not free:
        return None, "Every curve in that STEP file is an edge of a face. The spine needs to be a separate curve."
    length = lambda p: float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
    best = max(free, key=lambda i: length(free[i]))
    return free[best], f"{len(free)} free curve(s) found; using the longest ({length(free[best]):.1f} in)."
