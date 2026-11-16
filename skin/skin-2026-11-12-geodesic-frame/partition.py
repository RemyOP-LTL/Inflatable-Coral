#!/usr/bin/env python3
"""
Which spokes belong to which piece (Remy, 2026-11-16).

  PART        a pentagon plate plus ONLY the spokes at its five corners (its "arms"), one flat piece. The arms hinge at
              the corners (see frame.flatten) and fold where they leave the plate.
  SPINE SPOKE a spoke that runs from the edge of the spine out to a node. It is a tab of the spine piece.
  LOOSE       every other spoke: a separate strip, riveted at both ends. All loose spokes should be one length.

A spoke between two plate corners (two pentagons one spoke apart) stays loose: it cannot be the arm of both.
`band` = the nodes that sit on the edge of the spine (clip_spine.py makes them). A polygon that touches the band is a
partial window cut by the spine, never a plate.
"""


def partition(layout, band=()):
    polys = layout["polygons"]
    info = layout.get("polygon_info") or [{} for _ in polys]
    band = set(band)
    lost = {i for i, p in enumerate(polys) if any(v in band for v in p) or info[i].get("spine")}
    plates = [i for i, p in enumerate(polys) if len(p) == 5 and i not in lost]
    plate_of = {}
    plate_sides = set()
    for i in plates:
        p = polys[i]
        for v in p:
            plate_of.setdefault(v, i)
        plate_sides.update(frozenset(e) for e in zip(p, p[1:] + p[:1]))
    spokes = set()
    for p in polys:
        for a, b in zip(p, p[1:] + p[:1]):
            e = frozenset((a, b))
            if e not in plate_sides and not (a in band and b in band):
                spokes.add(e)
    spine_spokes = {e for e in spokes if len(e & band) == 1}
    tree, arms = set(), {}
    for i in plates:
        for v in polys[i]:
            for e in sorted(tuple(sorted(e)) for e in spokes if v in e):
                e = frozenset(e)
                w = next(iter(e - {v}))
                if e in spine_spokes or e in tree:
                    continue
                tree.add(e)
                arms.setdefault(i, []).append([v, w])
    loose = sorted(tuple(sorted(e)) for e in spokes if e not in tree and e not in spine_spokes)
    root, depth = {}, {}
    for i in plates:
        for v in polys[i]:
            root[v] = i; depth[v] = 0
        for v, w in arms.get(i, []):
            if w not in root:
                root[w] = i; depth[w] = 1
    return dict(plates=plates, tree=sorted(tuple(sorted(e)) for e in tree), loose=[list(e) for e in loose],
                arms={str(k): v for k, v in arms.items()}, spine_spokes=sorted(tuple(sorted(e)) for e in spine_spokes),
                root={str(k): v for k, v in root.items()}, depth={str(k): v for k, v in depth.items()},
                lost=sorted(lost), band=sorted(int(v) for v in band))
