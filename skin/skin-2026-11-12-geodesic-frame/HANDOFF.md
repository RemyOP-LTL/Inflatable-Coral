# Hand-off: the geodesic-frame skin (read this first in a new session)

Written 2026-11-16. Remy is a mechanical engineer, very good at CAD, new to coding and git. Explain in plain language, no jargon, one recommended path, and say what a script does before asking him to run it. Remy now wants to work **locally on his Mac**, so everything lives in his repo folder and no cloud link is needed.

## The idea in one paragraph
The skin is a frame of **spokes** (plastic strips, 1.25 in wide, with a half circle at each end, 0.25 in rivet holes). Each pentagon is a solid plate with the polyp hole. A plate plus the spokes attached to it is one flat **part** cut on the CNC router from a 4 x 8 ft corrugated plastic sheet. Every other spoke is a **loose spoke**: a separate piece, riveted at both ends, cut inside a window of the flat part, with a router gap (default 0.125 in) all round. **All loose spokes should be one length.** Spoke length is measured between the centres of the two end half circles.

## Decisions Remy has made
- Spokes and ends 1.25 in. Rivet hole 0.25 in. Pentagon plate style A (the plate is the pentagon).
- Only the loose spokes need to be equal length (they are, within about 1 %).
- Main test shape: the bent tube stood up as a **smile** (ends curve up, lowest point on the z = 0 plane), with a **4 in spine** along the top line on the inside of the curve. Dome is the secondary shape.
- Spine version **B** (layout built around the spine, so almost no pentagon is lost) with a **live edge**: the outline flows out to every attachment point and eases back to about 4 in between.
- Not merging into main until he says so. Ignore the "section of 3D shapes" question for now.

## What is built (all in `skin/skin-2026-11-12-geodesic-frame/`)
- `layouts/smile-tube` (main) and `layouts/dome-equal5`; sources in `layouts/_sources/`.
- `frame.py` (the maths), `partition.py` (which spokes are attached vs loose), `equalize.py` (makes loose spokes one length), `spine.py`, `spine_layout.py`, `build_smile.py` (the chain that makes the smile tube with the spine), `patch_draw.js` (nests loose spokes, checks gaps, draws), `frame_app.py` + `frame_page.html` (the preview page), `make_snapshot.py` (builds `snapshot.html`, the same page as one file).
- Plain notes and exact rebuild commands are in `skin/CLAUDE.md` (sections "Update 3", "4", "5").

## How Remy runs it on his Mac (no cloud needed)
1. In Finder open the repo folder, then `skin/skin-2026-11-12-geodesic-frame/`.
2. Double-click `Start Frame Tool.command`. It opens the tool in his browser at http://127.0.0.1:8790/.
3. One-time setup: the tool needs Python with `numpy`, `scipy`, `matplotlib` and `shapely` (`requirements.txt` in this folder). If double-clicking fails, the session should install them for him and say what it is doing.
(Or open `snapshot.html` in the browser: the same page with the data baked in, no server needed. Its 3D view needs internet.)

## Open items
- Pull request #7 (https://github.com/RemyOP-LTL/Inflatable-Coral/pull/7) is open, not merged. Ask Remy before merging.
- Ports: 8790 is the frame tool. The polyp session also used 8820 for another tool, which is why this tool moved. Proposed ranges (needs a one-line change in the root `CLAUDE.md`, not yet made): skin 8760-8799, polyps 8800-8859, lighting 8860-8879, shared 8880-8899. Working locally in one session removes most of this confusion.
- Ask whether the spine's live edge has the right amount of pumpiness (can be lumpier or smoother).
- Next work: make the spine its own flat part with its attached spokes; nest all the loose spokes (one length) on the 4 x 8 ft sheet in bulk; better cells (some are skewed); then get the flat parts into Fusion 360 (SVG import is the quick route). Hole size versus the polyp (5 in cuff) is still undecided.

## Known limits
- Equal length of the attached spokes is not possible while keeping cells round; some cells are skewed (smallest angle at a node about 50 degrees).
- Layout building needs `shapely`; the tool does not.
- Not yet run on a Mac. First thing to do locally: run it and report what breaks.
