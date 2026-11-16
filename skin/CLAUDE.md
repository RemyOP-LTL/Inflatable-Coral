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
**Hand-off for a new session: `skin/skin-2026-11-12-geodesic-frame/HANDOFF.md` (2026-11-16, plain language; Remy now works locally on his Mac).**

Layout prototype exists, outside Fusion. Nothing built in Fusion 360 yet. At default settings on the test tube: 58 pentagons, about 23 % coverage, about 5 in across, no two touching; shapes about 0.27 in out of flat on average.
The layout now works on any surface given as a mesh (2026-11-02). Tried on the tube as a mesh (76 pentagons, 24 %), a 48 in dome (44 pentagons, 25 %, 0.04 in out of flat) and a lumpy dome (47 pentagons, 25 %, 0.22 in out of flat). Not tried on a real Fusion export yet.

## Done this session (2026-11-15): geodesic-frame concept, first prototype (branch `skin-2026-11-12-geodesic-frame`)
All new work is in `skin-2026-11-12-geodesic-frame/`. Nothing else in `skin/` was touched.
- **Concept (Remy):** the skin as a geodesic-style frame. Hubs = the corners of today's polygons (3 spokes each). Spokes = polygon edges, 1 in wide. A 1.5 in circle at every hub. Pentagons = solid plates with the polyp hole (an "oversized hub"). Hexagons and heptagons are open windows. Laid flat, a patch (one pentagon plus rings of windows) does not close; spokes that come up short keep a free 1.5 in circle that is pulled to its hub and riveted (0.25 in holes, only where a rivet goes).
- **Decisions:** hub spacing 5 in (a setting, `--edge`); corrugation direction ignored for now; tube is the main shape, dome second; one ring of windows is the working patch size. Not yet answered by Remy: which joints are cut (the tool cuts the spoke that closes each window; free end kept by the hub nearer the plate), and which pentagon-plate style he wants (see below).
- `frame.py`: the maths (frame from layout.json, flattening a patch, pull distances, sheet fit, SVG at 1 unit = 1 in). Checked: on a flat honeycomb the pull is 0.00 in.
- `frame_app.py` + `frame_page.html`: browser tool on **port 8820** (`Start Frame Tool.command`, or `python3 frame_app.py`). 3D frame, click a pentagon, flat patch, sliders for rings / spoke width / circle / rivet hole, plate style (pentagon outline or round hub, or both side by side), SVG download, and "Make a new layout" (runs `hex57_mesh.py --edge N` into `runs/`, git-ignored). Tested in a real browser here (needs the 3D library from the internet; tested with a local copy).
- `layouts/tube-edge5`, `layouts/dome-edge5`: layouts at 5 in spacing (tube 16 in across, dome 48 in). `snapshot.html` (built by `make_snapshot.py`) is the link page.
- **Results (1 ring):** every patch has 5 cut spokes; typical longest pull 1.8 in on the tube (worst 3.4), 0.7 in on the dome; patches are about 26 in across and fit a 4 x 8 ft sheet. With 2 rings several other pentagons fall inside the patch (their plates are not kept rigid yet), and pulls grow to 4 in typical, 10 in worst.
- Observation: at 5 in spacing the tube's panels are about 8 in across and 0.8 in out of flat on average, the "playing card on a can" effect from before.
- Port 8820 is not yet in the root CLAUDE.md ports list (outside `skin/`, so left for Remy to approve).

### Update (2026-11-15, later): loose spokes, smile tube with spine, equal-length rule
Words now (Remy): there is no hub. A **spoke** is a strip with a half circle at each end; its **length** is measured between the centres of the two end half circles. A **node** is where spoke ends meet. Spoke width = end diameter = **1.25 in** (decided). Rivet hole 0.25 in. Router gap 0.125 in (setting).
- **Plate style A** (plate = the pentagon outline) chosen. Round hub removed.
- **Overlap bug (Remy):** with 1 in spokes and 1.5 in end circles, the two ends to be pinned landed on top of each other in the flat. A "swing apart" step was tried first; it is gone. **New structure (Remy's idea):** every orange (cut) spoke is a **loose, separate piece**, riveted at both ends, and in the flat CNC pattern it is **nested inside a window** of the body (plate + attached spokes) with a router gap all round. No pull needed. Checked with an independent geometry library: 226 loose spokes over all patches, nearest 0.198 in from anything, none closer than the router gap; 1-ring patches have no body overlaps (2 rings do, because other pentagons inside are not rigid yet). At 1.25 in, 40 of 41 loose spokes on the smile tube sit in a window and the last still has clear space.
- **(Superseded, see "Update 3" below.) Equal-length rule, first try (all spokes):** `equalize.py` nudges nodes along the surface so every spoke (every polygon edge that is not a pentagon side) gets one length while pentagons stay regular and cells stay roundish. Honest result: it **cannot reach equal** on the existing net while keeping cells round. Interior spoke length spread went from 13.8 % to about 5 % (tube) and 15.5 % to about 3 to 10 % (dome); at 1 % spread cells collapse (node angles of 5 to 7 degrees). The smile tube's page figure (about 9 %) also counts the 6 pentagon plates lost to the spine, whose sides become 5.7 in spokes. The real fix is in the layout generator (uniform cells); not started. I read "them" as all spokes; if Remy meant only the loose ones, the rule is much easier (only those need one length).
- **Smile tube with spine:** `spine.py` stands the bent test tube up (bend plane vertical, inside of the bend up, lowest point on z = 0, Fusion's Top plane), lays a **4 in wide spine** along the top line on the inside of the curve (92.8 in long), drops the nodes inside it, and ends each spoke that ran into it at a **round bump with a 0.25 in rivet hole** (13 bumps). Pentagon plates touching the spine are lost (6 of 20: no polyp there). TUBE-SPECIFIC (uses BEND_RADIUS and TUBE_RADIUS). Result in `layouts/smile-tube/` (primary shape); dome (`layouts/dome-equal5`) is secondary. Sources/intermediate layouts are in `layouts/_sources/`.
  To rebuild: `python3 equalize.py layouts/_sources/tube-edge5/layout.json --out layouts/_sources/tube-equal5 --anchor 0.05 --round 0.1` then `python3 spine.py layouts/_sources/tube-equal5/layout.json --out layouts/smile-tube`.
- **Tool (port now 8790, see Update 3):** 3D view draws spokes as flat strips lying on the surface, pentagons as plates with the polyp hole, and the spine with its bumps and holes; "Show only the selected section" shows that section's 3D shapes by themselves; the flat section and the flat spine can be downloaded as SVG. `snapshot.html` (built by `make_snapshot.py`) is the same flat views as a standalone page (2D only).
- Interpretation to confirm with Remy: "see the section of 3D shapes" taken as the 3D view of the selected patch as real plastic shapes (done), not a cut-through cross section.
- `patch_draw.js` does the nesting, checks and drawing; `frame.py` flattens (`patch_data`) and knows about the spine (hidden spokes, lost plates).

### Update 3 (2026-11-15, evening): only the loose spokes are equal, two spine versions, port moved
- **Remy's answers:** only the loose orange spokes must be one length (done below); show examples of both spine options (done); ignore the "section of 3D shapes" question for now; the port clash is real (below).
- **Partition (`partition.py`):** every pentagon plate plus the tree of spokes grown out from it is one flat PART; every other spoke is LOOSE (numbered). Grown breadth first from all plates at once, ties by node number, so it depends only on connections. Spokes ending in the spine are always loose. About half of all spokes are loose.
- **`equalize.py` now equalises only the loose spokes** (attached spokes get a gentle pull, pentagon plates stay regular, cells stay roundish; pentagons on the spine are treated as windows). Result: loose spokes within about 1 % of each other (smile tube 4.67 to 4.95 in; version B 4.58 to 4.81 in; dome 4.22 to 4.57 in). Attached spokes vary (3.8 to 5.8 in) and some cells are skewed (smallest angle at a node about 50 degrees).
- **`build_smile.py`** runs the whole chain (band, partition, equalise, smile + spine). Rebuild: `python3 build_smile.py layouts/_sources/tube-edge5/layout.json --out layouts/smile-tube`.
- **Spine, two versions (Remy asked to see both):** A `layouts/smile-tube`: spine cut through the existing layout: 20 pentagons, 6 lost, 12 bumps (4.5 to 14.7 in apart). B `layouts/smile-tube-clear`: `spine_layout.py` re-runs hex57 with one extra rule (no new pentagon seeded near the spine): 17 pentagons, 1 lost (an equalising nudge moved one), 16 bumps (2.2 to 9.6 in apart). B has about 15 % fewer pentagons. `spine_layout.py` copies hex57's `add_pair` with one extra test; hex57 itself is untouched. Rebuild B: from `skin/hex57`: `SPINE_KEEP_OUT=9.2 python3 ../skin-2026-11-12-geodesic-frame/spine_layout.py meshes/tube.obj --edge 5 --out ../skin-2026-11-12-geodesic-frame/layouts/_sources/tube-clear5`, then `build_smile.py` on it.
- **Tool and flat sections:** the rings slider is gone (a part is defined by the partition). The flat sheet of a part shows the plate, its attached spokes, and the loose spokes assigned to it (the spoke whose end is nearer the plate; ties by plate number) nested in windows; each loose end is numbered where it rivets (spine ends in purple). 11 of 12 parts on version A have every loose spoke in a window; the 12th still has clear space.
- **PORT:** the frame tool is now **8790** (was 8820). The polyp session's branch `polyp-2026-11-15-spiral-cone` already used 8820 for its spiral-cone tool. Both sessions followed the same rule ("next block is 8820") from `main`, which neither had merged. Proposal for Remy (needs a small change to the root `CLAUDE.md`, not made here): fixed ranges per area, skin 8760-8799 (skin_app 8765.., frame tool 8790), polyps 8800-8859 (polyp tool 8800, spiral-cone 8820), lighting 8860-8879, shared 8880-8899; every tool also moves up to the next free port in its own range and prints its link.

### Update 4 (2026-11-16): one link, nothing to run
Remy was confused about where things run and wants one click after every change. `snapshot.html` (built by `make_snapshot.py`) is now the **whole frame tool as one page**: 3D tube, flat sections, spine, all layouts and every part baked in (same code as the local tool), published as the Artifact link. After every change: run `python3 make_snapshot.py`, republish `snapshot.html`, give Remy the link. The Mac tool (`Start Frame Tool.command`, port 8790) is optional now (only needed for "Make a new layout" and SVG download). The 3D library loads from the internet (jsdelivr); tested here with a local copy.

### Update 5 (2026-11-16): spine B chosen, live edge
- **Remy chose B** (layout built around the spine). `layouts/smile-tube` is now B; version A moved to `layouts/_sources/smile-tube-cut-through` (not listed).
- **Live edge (Remy):** the spine outline flows organically out to every attachment point (16 on the tube) and eases back to about 4 in between, with a gentle wave of its own (`spine.organic_outline`: 4 in strip plus a swelling round each attachment, closing and opening smoothing, then triangulated so it can be drawn on the curved tube). Width: 3.6 to 6.4 in, mean 4.5; every attachment end plus rim sits inside. The old round bumps are gone. Needs the `shapely` library, but only when building layouts (`build_smile.py`), not for the page or the tool.
- Rebuild: `python3 build_smile.py layouts/_sources/tube-clear5/layout.json --out layouts/smile-tube` (the `tube-clear5` layout comes from `spine_layout.py`, see Update 3).

## Next (frame concept)
- Remy to approve the port ranges in the root `CLAUDE.md`.
- Make the spine its own flat part with its attached spokes, nest all loose spokes (all one length) for the 4 x 8 ft sheet in bulk, check part sizes against the sheet.
- Better cells: the equalising leaves some skewed cells; a layout generator that builds toward equal loose spokes would fix that.
- Union each patch into one cut outline, nest on the sheet, then into Fusion (SVG import is the quick route).

## Done this session, second round (2026-11-02): holes, cutouts, extension, scale, tabs
Remy asked for six things; all built and tested (details in `hex57/README.md`, last section):
- Scale bar and skin size in the 3D viewer.
- "New tab" in the browser tool; each tab runs its own job (up to 3 at once).
- Pentagon size set by hole diameter plus rim (`--hole-diameter`, `--hole-rim`); the tool shows the resulting pentagon size and warns when it is too big for the hexagons.
- "Weirdness": read as the cut-off, trimmed edges. The surface is now extended past each open edge (`--extend-rows`, default 2) so the shapes along Remy's edge are whole; extension shapes are greyed and not counted. If Remy meant other weirdness, ask what he saw.
- Round holes cut out of every full pentagon; every other full panel gets a cutout following its outline, thin rim mid-side and wide at corners (`hex57/cutouts.py`). Real see-through holes in the viewer; loops saved in layout.json.
- Decisions: cutouts defaults 0.5 in mid-side, 1.0 in at corners; panels touching an open edge stay solid; hole diameter is fixed, so the rim varies and the thinnest is reported next to what was asked.
- Known issue: because pentagons come out a few percent irregular, the thinnest rim round a hole is about 0.32 in when 0.5 in is asked. Fix options: aim pentagons larger (`HEX57_PENT_AIM`, costs roundness of neighbours), or ask for a thicker rim. Needs Remy's call.
- Testing note: the viewer was checked in a real browser here with the 3D library served locally. The new tab, running two jobs at once, uploads and failed runs were tested. Not run on Remy's Mac (Python 3.9, syntax checked only).

## Done earlier this session (2026-11-02): layout on any surface
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
- Decide how to handle the thin rim round pentagon holes (see known issue above).
- Not done yet from this round: flat sections for the router bed, tabs and rivets; how it gets into Fusion (the cut loops are in layout.json, ready for that).
- Remy to try the browser tool on his Mac (Python 3.9; syntax checked, not run on 3.9) and report what breaks.
- Try it on a real Fusion export (a branch or the brain-coral dome): check units, outward direction and open edges. Untested: closed tube tip with a narrow neck, Y-fork, sharp creases.
- Dome-specific question: on a dome the rim shapes are cut off; decide how the dome's base edge should end.
- Edge-thinning cutout in each polygon.
- Flat sections for a 4 x 8 ft sheet, with tab and rivet details.
