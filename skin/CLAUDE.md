# skin/

## Purpose
A flexible tool that applies a slightly bumpy "polygon" skin, made from sections of plastic, to a surface shape. It then splits the skin into flat sections that can be cut from a 4 x 8 ft sheet.

## Design intent (from Remy)
- Material: corrugated plastic sheet, 1 mm wall. Simulate only the top layer for now.
- Test shapes: tube 12-16 in across; later a domed brain-coral shape. The method should work on any surface, not just a tube.
- Pentagons are evenly distributed across the surface. Each pentagon carries one polyp (a hole for the polyp; see `polyps/`).
- Every polygon is close to equal-sided: corners about the same distance from the centre, and roughly flat. The plastic bends and stretches a bit, so corners need not meet perfectly.
- Each polygon is cored out as an offset of its outer shape, leaving a rim that thins toward the middle of each shared edge.
- The finished skin is split into sections of attached polygons that lie flat and fit on a 4 x 8 ft sheet. The 3D shape comes from joining neighbouring edges with tabs and rivets.

## What's here
- `hex57/` — latest layout work, copied unchanged from `RemyOP-LTL/Modeling` (`hex-tubes/layouts/hex57`, main branch, 2026-10-30). A standalone Python script lays hexagons, pentagons (never touching) and heptagons on a test tube and opens a 3D viewer in the browser. Start with `hex57/HANDOFF.md`, then `hex57/README.md`.
- `reference/FUSION-CONTEXT.md` — background and lessons from the Onshape work.

To run it (Mac): `pip3 install numpy scipy matplotlib`, then in `skin/hex57/` run `python3 hex57_layout.py` (about 70 s) and open `viewer.html`.

## Status
Layout prototype exists, outside Fusion. Nothing built in Fusion 360 yet. At default settings: 58 pentagons, about 23 % coverage, about 5 in across, no two touching; shapes about 0.27 in out of flat on average.

## Open questions
- Hole size vs pentagon size (see `hex57/HANDOFF.md`): smaller hole, or bigger bowed pentagons? Now that the round hole is replaced by an edge-thinning offset cutout, this needs revisiting.
- The older notes say the plastic "can flex but not stretch"; Remy now says it can bend and stretch a bit. Confirm how much, since shared edge lengths depend on it.
- Pentagon spacing is set by where the polyps go, so polyp size sets pentagon size.

## Next
- Decide how the layout gets into Fusion 360 (`layout.json` import by a Fusion Python script is the likely route; check what Python libraries Fusion has).
- Make the layout work on a dome as well as a tube.
- Edge-thinning cutout in each polygon.
- Flat sections for a 4 x 8 ft sheet, with tab and rivet details.
