"""Sketch v2: hubs = polygon corners (3 spokes each), spokes = polygon edges (1 in wide),
1.5 in circle at every corner, pentagons filled solid with the round polyp hole.
Run: python3 sketch_reading2.py  -> reading_sketch2.png"""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
here = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(here, "..", "hex57", "layouts", "dome", "layout.json")))
V = np.array(d["vertices"]); polys = d["polygons"]; info = d["polygon_info"]
C = np.array([i["centre"] for i in info]); sides = [i["sides"] for i in info]
pent = [p for p in range(len(polys)) if sides[p]==5 and not info[p]["end"]]
h = min(pent, key=lambda p: np.hypot(*(C[p][:2]-np.mean(C[:,:2],axis=0)))); c0 = C[h][:2]
fig, ax = plt.subplots(figsize=(9,9))
edges = set()
for p, poly in enumerate(polys):
    for a, b in zip(poly, poly[1:]+poly[:1]): edges.add(frozenset((a,b)))
for e in edges:
    a, b = tuple(e); ax.plot(*V[[a,b]][:,:2].T, c="#2a6", lw=7.5, solid_capstyle="butt", alpha=.85)  # ~1 in wide at this scale
for p, poly in enumerate(polys):
    if sides[p]==5 and not info[p]["end"]:
        ax.add_patch(Polygon(V[poly][:,:2], fc="#e07b00", ec="none", alpha=.9))
        ax.add_patch(Circle(C[p][:2], d["params"]["HOLE_DIAMETER"]/2, fc="white", ec="k", lw=.8))
used = {v for poly in polys for v in poly}
for v in used:
    ax.add_patch(Circle(V[v][:2], .75, fc="#2a6", ec="k", lw=.5)); ax.add_patch(Circle(V[v][:2], .125, fc="white", ec="k", lw=.4))
ax.set_xlim(c0[0]-17, c0[0]+17); ax.set_ylim(c0[1]-17, c0[1]+17); ax.set_aspect("equal")
ax.set_title("Reading v2 (dome from above, inches): green = 1 in spokes with 1.5 in hub circles (0.25 in holes) at every corner;\norange = pentagon as an oversized hub with the polyp hole")
fig.savefig(os.path.join(here, "reading_sketch2.png"), dpi=110, bbox_inches="tight")
