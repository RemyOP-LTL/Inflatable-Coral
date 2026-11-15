#!/usr/bin/env python3
"""
Which spokes are attached and which are loose (Remy, 2026-11-15).

Every pentagon plate with the spokes attached to it is one flat PART. Every other spoke is a LOOSE spoke,
riveted at both ends, and all loose spokes should be the same length.

Rule used here: grow a tree of attached spokes outward from every plate at the same speed (breadth first, ties
broken by node number, so the result depends only on how the nodes connect, not on where they sit). A spoke
that is not in any tree is loose. Spokes that end in the spine are always loose (they rivet to the spine's
bumps). Spokes with both ends in the spine do not exist.
"""
from collections import deque


def partition(layout, band=()):
    polys = layout["polygons"]
    band = set(band)
    lost = {i for i, p in enumerate(polys) if any(v in band for v in p)}        # polygons touching the spine
    plates = [i for i, p in enumerate(polys) if len(p) == 5 and i not in lost]
    plate_sides = set()
    for i in plates:
        p = polys[i]
        plate_sides.update(frozenset(e) for e in zip(p, p[1:] + p[:1]))
    spokes = set()
    for p in polys:
        for a, b in zip(p, p[1:] + p[:1]):
            e = frozenset((a, b))
            if e not in plate_sides and not (a in band and b in band):
                spokes.add(e)
    forced = {e for e in spokes if len(e & band) == 1}                          # a spoke into the spine
    adj = {}
    for e in spokes - forced:
        a, b = tuple(e)
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    root, parent, depth, tree = {}, {}, {}, set()
    frontier = []
    for i in plates:
        for v in polys[i]:
            root[v] = i; depth[v] = 0; frontier.append(v)
    frontier.sort()
    while frontier:
        nxt = []
        for x in frontier:
            for y in sorted(adj.get(x, [])):
                if y not in root:
                    root[y] = root[x]; parent[y] = x; depth[y] = depth[x] + 1
                    tree.add(frozenset((x, y))); nxt.append(y)
        frontier = sorted(nxt)
    loose = sorted(tuple(sorted(e)) for e in spokes if e not in tree)
    for v in {v for e in spokes for v in e}:                                    # nodes no tree reached
        if v not in root and v not in band:
            root[v] = -1; depth[v] = 0
    return dict(plates=plates, tree=sorted(tuple(sorted(e)) for e in tree), loose=[list(e) for e in loose],
                root={str(k): v for k, v in root.items()}, depth={str(k): v for k, v in depth.items()}, lost=sorted(lost), band=sorted(int(v) for v in band))
