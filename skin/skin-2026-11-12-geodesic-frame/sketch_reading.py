"""Sketch of the hub-and-spoke reading, drawn from an existing layout.json.
Hubs = polygon centres (seeds). Spokes = links between hubs whose polygons share an edge.
Run: python3 sketch_reading.py  (writes reading_sketch.png next to this file)"""
import json, os, itertools
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
here = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(here, "..", "hex57", "layouts", "dome", "layout.json")))
V = np.array(d["vertices"]); polys = d["polygons"]; info = d["polygon_info"]
C = np.array([i["centre"] for i in info]); sides = np.array([i["sides"] for i in info])
edge = {}
for p, poly in enumerate(polys):
    for a, b in zip(poly, poly[1:] + poly[:1]):
        edge.setdefault(frozenset((a, b)), []).append(p)
links = [tuple(v) for v in edge.values() if len(v) == 2]
nb = {}
for a, b in links: nb.setdefault(a, []).append(b); nb.setdefault(b, []).append(a)
pent = [p for p in range(len(polys)) if sides[p] == 5 and not info[p]["end"] and all(not info[q]["end"] for q in nb.get(p, []))]
fig, ax = plt.subplots(figsize=(9, 9))   # top-down view of the dome
for p, poly in enumerate(polys):
    xy = V[poly][:, :2]; ax.fill(*xy.T, fc="#f4ecd8" if sides[p] != 5 else "#f6c28b", ec="#bbb", lw=.6)
for a, b in links: ax.plot(*C[[a, b]][:, :2].T, c="#c33", lw=1)
col = {5: "#e07b00", 6: "#444", 7: "#1f6fd0"}
for p in range(len(polys)): ax.plot(*C[p][:2], "o", ms=3.5, c=col.get(sides[p], "k"))
if pent:
    h = pent[len(pent)//2]
    for q in nb[h]: ax.plot(*C[[h, q]][:, :2].T, c="#e07b00", lw=3.5)
    ax.plot(*C[h][:2], "o", ms=16, mfc="none", mec="#e07b00", mew=2.5)
    ax.set_xlim(C[h][0]-22, C[h][0]+22); ax.set_ylim(C[h][1]-22, C[h][1]+22)
ax.set_aspect("equal"); ax.set_title("Reading: dots = hubs (orange 5-spoke, grey 6, blue 7); red lines = spokes;\nthick orange = one 5-spoke patch (hub + 5 spokes). Dome seen from above, inches")
fig.savefig(os.path.join(here, "reading_sketch.png"), dpi=110, bbox_inches="tight")
print("pentagons", len(pent), "links", len(links), "hub valence counts", {k: sum(1 for p in nb if len(nb[p])==k) for k in (5,6,7)})
