# Design bundle formats (the contract between the parts)

Why this file exists: the skin, the polyp and the workbench are made in different sessions on
different branches. They only need to agree on **what a saved design looks like**. Any session can
change its generator freely, as long as the file it writes follows this page. The workbench
(`workbench/`) reads these files from any branch or tag, so nothing has to be merged to main to be viewed.

Rules for both: plain JSON, UTF-8, units in **inches**, +z is "up" in the part's own coordinates.
Extra fields are allowed and ignored by the viewer; never rename or remove the ones below without
telling the planning session. Find-by-name: the workbench lists every file called
`layout.json` (skin) or `polyp.json` (polyp) in a branch, except under a folder starting with `_`.

## Skin bundle: `layout.json` (the existing hex57 file, unchanged)
Written by `skin/hex57/hex57_layout.py` and `hex57_mesh.py`, and already by the geodesic-frame session.
Fields the workbench needs:
| Field | Meaning |
|---|---|
| `units` | `"inch"` |
| `vertices` | list of `[x, y, z]` corners, shared by neighbouring panels |
| `polygons` | list of corner-index lists, anticlockwise seen from outside |
| `polygon_info[i]` | one entry per polygon, same order: `sides`, `end` (true = cut-off extension, not counted), `across`, `centre` `[x,y,z]`, `normal` `[x,y,z]` (unit, pointing **out** of the skin) |
| `params.HOLE_DIAMETER` | diameter of the round polyp hole in every pentagon |
A **polyp spot** = a polygon with `sides == 5` and `end == false`. Checked 2026-11-16 on hex57 dome/tube and the geodesic-frame `dome-equal5`: all carry `centre`, `normal`, `HOLE_DIAMETER`, so **the existing file is the contract as it is**.

Optional, not required yet (add when a design needs it; the combined tab will use them if present):
`polygon_info[i].spin_deg` (turn the polyp about its axis), `polygon_info[i].hole_diameter` (per-pentagon hole).
Geodesic-frame session: nothing needs adding for placement. If its panels are not flat polygons (hubs, spokes), keep writing `polygons` as the outline of each panel so the viewer can draw it, and add your own extra fields freely.

## Polyp bundle: `polyp.json` (new, 2026-11-16)
Written by `polyps/fabric-pattern/export_bundle.py` (5-finger). The spiral-cone session should write the same shape.
```
{ "format": "coral-polyp-bundle", "version": 1, "name": "...", "units": "inch",
  "frame": "origin = centre of the cuff bottom (meets the skin); +z = straight out of the skin",
  "mesh":  { "vertices": [[x,y,z],...], "triangles": [[a,b,c],...] },   // inflated outer surface, outward-facing
  "size":  { "footprint_diameter": ..., "height": ..., "reach_radius": ..., "tube_diameter": ... },
  "settings": { ...whatever the design's parameters were... },
  "pattern":  { "files": ["relative/path/to/pattern.pdf", ...] } }
```
- `footprint_diameter`: diameter of the ring that meets the skin (compared with the skin's `HOLE_DIAMETER`).
- `reach_radius`: widest distance of any point from the axis (compared with the spacing between pentagons).
- The cuff centre sits at the origin and the axis is +z, so the combined tab places a polyp at a pentagon `centre` and turns +z onto the pentagon `normal`.
- Where to put them: a folder per design, e.g. `polyps/<part>/bundles/<design-name>/polyp.json`. Put your experiment's name in the folder (the same name as the branch where it helps).

## Versions
A "version" is just a git branch or tag. Keep a chosen result by tagging it (`<area>-<date>-<idea>-v1`) or copy the bundle to a `designs/` folder; the workbench shows both.
