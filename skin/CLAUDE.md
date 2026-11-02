# skin/

## Purpose
A flexible tool that applies a slightly bumpy "polygon" skin, made from sections of plastic, to a surface shape. It then splits the skin into flat sections that can be cut from a 4 x 8 ft sheet.

## Design intent (from Remy)
- Material: corrugated plastic sheet, 1 mm wall. Simulate only the top layer for now.
- Test shapes: tube 12-16 in across; later a domed brain-coral shape. The method should work on any surface, not just a tube.
- Pentagons are evenly distributed across the surface. Each pentagon carries one polyp (a hole for the polyp; see `polyps/`).
- Every polygon is close to equal-sided: corners about the same distance from the centre, and roughly flat. The plastic bends but is assumed not to stretch; small corner mismatches are fine as long as shared edge lengths match.
- Pentagons get a normal round hole for the polyp. Every other polygon is cored out as an offset of its outer shape, leaving a rim that thins toward the middle of each shared edge.
- The finished skin is split into sections of attached polygons that lie flat and fit on a 4 x 8 ft sheet. The 3D shape comes from joining neighbouring edges with tabs and rivets.

## What's here
- `hex57/` — latest layout work, copied unchanged from `RemyOP-LTL/Modeling` (`hex-tubes/layouts/hex57`, main branch, 2026-10-30). A standalone Python script lays hexagons, pentagons (never touching) and heptagons on a test tube and opens a 3D viewer in the browser. Start with `hex57/HANDOFF.md`, then `hex57/README.md`.
- `hex57/hex57_mesh.py` — (new, 2026-11-02) runs the same layout on any mesh file (OBJ or STL). `hex57/make_test_meshes.py` makes test shapes in `hex57/meshes/` (bent tube, dome, lumpy dome); results are in `hex57/layouts/`.
- `reference/FUSION-CONTEXT.md` — background and lessons from the Onshape work.

**Easiest (Mac):** double-click `hex57/Start Skin Tool.command`: a browser page with a shape picker, sliders and a Run button (see the last section of `hex57/README.md`).
To run it from Terminal (Mac): `pip3 install numpy scipy matplotlib`, then in `skin/hex57/` run `python3 hex57_layout.py` (about 50 s) and open `viewer.html`.
To run it on any shape from a mesh file: `python3 hex57_mesh.py meshes/lumpy_dome.obj` (or your own OBJ/STL; add `--units mm` if it is in millimetres), then open `layouts/<name>/viewer.html`. See the last section of `hex57/README.md`.

## Status
Layout prototype exists, outside Fusion. Nothing built in Fusion 360 yet. At default settings on the test tube: 58 pentagons, about 23 % coverage, about 5 in across, no two touching; shapes about 0.27 in out of flat on average.
The layout now works on any surface given as a mesh (2026-11-02). Tried on the tube as a mesh (76 pentagons, 24 %), a 48 in dome (44 pentagons, 25 %, 0.04 in out of flat) and a lumpy dome (47 pentagons, 25 %, 0.22 in out of flat). Not tried on a real Fusion export yet.

## Done this session (2026-11-02): layout on any surface
- Split `hex57_layout.py`'s `main()` into the tube setup plus a reusable `run_layout(...)`. The tube result is unchanged (checked: identical corners and polygons before and after). Small changes: `settle` handles any number of open edges (was hard-coded to two), `HEX57_EDGE` environment variable can override `EDGE`, layout.json params now carry the surface settings passed in, and `measure` copes with a surface that has no cut-off shapes.
- New `hex57_mesh.py`: reads OBJ/STL (units option), welds corners, keeps the biggest piece, orients triangles outward, finds open edges, samples the surface densely, starts from the mesh's own triangles and calls `run_layout`.
- Remy found Terminal awkward and asked for a window to run and tweak the tool. Built `hex57/skin_app.py`, a browser page (standard-library web server, local only) launched by double-clicking `hex57/Start Skin Tool.command`. Controls (chosen by Remy): shape file (examples or upload, with units and an inside-out switch), hexagon side length, pentagon size ratio, pentagon coverage, hole rim, seed. Each Run starts `hex57_mesh.py` in the background, shows progress, then shows the 3D viewer in the page and keeps the run in `hex57/runs/`. Tested in a browser here (upload, sliders, run, results list, failed run); the 3D viewer itself needs the internet and could not be seen from the test environment. The settings also exist as `hex57_mesh.py` options (`--pent-ratio`, `--coverage`, `--hole-rim`, `--seed`).
- Decisions: mesh triangles are the starting seeds (the old tube-only honeycomb start is not needed); shapes at an open edge are cut and left out of the counts; no "extra length" trimming on meshes (give the mesh extra surface instead); `--out` defaults to `hex57/layouts/<mesh name>/`.
- The tube-only code that remains: `TestTube`, `start_honeycomb`, the unrolled picture. All marked TUBE-SPECIFIC.

## Open questions
- **Hole size vs the polyp (deferred by Remy, 2026-10-30; the goal is generalized tools, matching comes later):** the polyp cuff slides over a 5 in tube, so the pentagon hole must be at least about 5 in. `hex57/HANDOFF.md` says a 5 in hole needs pentagons about 6.45 in across, and the current layout gives about 5 in pentagons with a 3.75 in hole. Needs a decision (smaller polyp tube, bigger pentagons, or a different attachment).
- Plastic stretch: decided to assume none. Shared edge lengths must match.
- Pentagon spacing is set by where the polyps go, so polyp size sets pentagon size.

## Next
- (Deferred by Remy) Decide how the layout gets into Fusion 360 (`layout.json` import by a Fusion Python script is the likely route; check what Python libraries Fusion has).
- Remy to try the browser tool on his Mac (Python 3.9; syntax checked, not run on 3.9) and report what breaks.
- Try it on a real Fusion export (a branch or the brain-coral dome): check units, outward direction and open edges. Untested: closed tube tip with a narrow neck, Y-fork, sharp creases.
- Dome-specific question: on a dome the rim shapes are cut off; decide how the dome's base edge should end.
- Edge-thinning cutout in each polygon.
- Flat sections for a 4 x 8 ft sheet, with tab and rivet details.
