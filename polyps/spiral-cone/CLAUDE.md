# polyps/spiral-cone/

**Decision 2026-11-16 (Remy): this is its own tool, the "cone worm pattern simulator". It is NOT to be merged into the polyp tool or `main`. Remy is moving to a new session and working locally. Start with `HANDOFF.md`, which has the full summary.**

## Purpose
A second polyp design, started 2026-11-15 on branch `polyp-2026-11-15-spiral-cone`. It sits beside the 5-finger design in `../fabric-pattern/` (not changed). Remy's 5-finger prototype did not work as hoped and had too many pieces and seams in tight spaces to sew at the scale of dozens of polyps. Cutting is not the problem (laser).

## The design (Remy, 2026-11-15)
- A long cone made from ONE long strip of woven nylon wound in a spiral (like a barber pole) and sewn edge to edge, seams on the inside. The cone shape comes from the strip tapering.
- Tighter wind toward the tip: turns closer together near the tip. Not too tight (the tip pitch was loosened to 2 in).
- **Cuff built into the strip** (2 in tall, 130 mm = 5.12 in across at the cuff line, which slides over the 5 in = 127 mm tube). **No seam allowance on the open end of the cuff** (removed 2026-11-15, it made an "ear" on the flat pattern).
- **Finish:** the spiral seam turns into one straight seam for the last 2 in of the cone length (smooth blend over `TRANSITION`, default 2 in). **The cone comes to a point** (`TIP_DIAMETER = 0`, Remy 2026-11-16, the seam allowance still goes round the point). The string anchors at the point.
- **Frill (corrected by Remy 2026-11-16):** ONE long straight strip, not shaped pieces. Starts 3 in up the axis (from the cuff line) and runs to the end of the spiral seam. Single layer, solid 0.5 in seam allowance along the sewn edge; the part that stands out is slit into 0.25 in strands (laser cut) so a non-stretching fabric does not scrunch. Slits run from the sew line to the free edge.
- **Alignment tabs:** 0.5 in squares sticking out of the cut edges, at matching places on both cone edges and the frill (numbered 1..n), and on the straight seam (S1, S2). Remy tacks them together before sewing.
- Length about 10 in, base diameter and length are variables. Air enters through the cuff (a stitch seal is enough). Motion: collapses along its axis; one string anchored at the tip, straight down the axis.

## What's here
- `spiral_cone.py`: makes the flat pattern from settings. Writes `<name>.svg` (true size, inches, laser: red cut, blue sew, grey dotted cuff line), `<name>.png` (flat pieces and a 3D sketch), `<name>.txt` (numbers and checks). `python3 spiral_cone.py --out folder`; change settings with `CONE="LENGTH=12,PITCH_TIP=3" python3 ...`. Needs numpy, matplotlib, shapely only.
- `spiral_tool.py`: browser page with a field for every setting, port **8820** (http://127.0.0.1:8820/), with the same Version card and Get latest changes button as the polyp tool. `install-mac.sh`: one-time Mac setup (launchd agent `com.coral.spiraltool`). Tested here in a headless browser and with the Mac-only commands stubbed; not run on a real Mac yet.
- `polyp-2026-11-15-spiral-cone/`: the latest outputs, default settings. `snapshot.html`: the link page for Remy.
- It does not use the cloth simulation. `spiral_tool.py` optionally imports `polyp_tool.py` from `../fabric-pattern/` for the version card; without it (a stand-alone copy of this folder) everything else works. Tested stand-alone 2026-11-16.

## How the geometry works
A cone unrolls flat exactly, like a paper party hat. A seam winding up the cone becomes a spiral curve on the flat fan. The seam goes round theta(z) = 2 pi * integral of dz / pitch(z); over the last `TRANSITION` inches before the straight part the winding rate fades to zero, so the seam turns smoothly straight. The strip is the region between one turn of the seam and the next turn above it, starting as a thin wedge at the open end of the cuff and ending at the straight seam: its top edge on the last turn is the tip opening (one full turn), and the two straight edges are the two radial edges that meet in the straight seam.

The frill needs no geometry beyond its length: it is a straight strip as long as the seam it covers (14.7 in at the defaults), and the fringe strands each hang free. (Round 3 tried to flatten the frill as a flared curved strip and cut it in 3 pieces. That was wrong, see history.)

## Checked (2026-11-16, defaults)
Seam edge lengths bottom and top: 41.521 in both. Open-end arc 19.295 in = pi x its diameter. The apex is exactly at the origin (a point). Straight edges 2.064 in each (2 in along the axis). Radius at the cuff line exactly 130 mm / 2. Frill strip length 14.679 in = the seam above the frill start. Runs without errors for other lengths and diameters, an open tip, no straight part, a sharp corner (`TRANSITION=0`, which warns about touching tabs), the separate cuff band and other frill widths.

## Defaults and results (2026-11-16)
10 in cone above the cuff line, 130 mm at the cuff line, a point at the tip, pitch 3 in at the base to 2 in at the end of the spiral, spiral 3.4 turns (cuff included), spiral seam 41.5 in, frill on the last 14.7 in of it, straight seam 2 in to the point. Cone strip bounding box 20.6 x 22.8 in. Frill: one strip 14.7 x 3.0 in, 59 strands 0.249 in wide. 10 numbered tabs plus S1, S2. 2 pieces to cut. Flared cuff: 5.12 in at the cuff line, 6.14 in at the open end (the cone is steeper now it ends in a point). `CUFF_IN_STRIP=0` gives a separate straight band.

## Assumed, not decided (confirm with Remy)
- Frill strip: `RUFFLE_WIDTH` = 3 in cut width = 0.5 in solid allowance + 2.5 in of fringe. (If the 3 in is the fringe, set 3.5.)
- Frill start is measured from the cuff line (the top of the cuff) along the axis.
- Pitch 3 and 2 in; fabric width 58 in; the straight seam blends in over 2 in (`TRANSITION=0` for a sharp corner); slits stop at the sew line; strands are 0.25 in (adjusted a hair so they divide the length evenly).
- The frill stands at right angles to the cone surface.

## Open flags
- The 2.5 in fringe is longer than the cone's radius (0.51 in) where the spiral ends, so fringe from opposite sides overlaps near the top. The tool warns. It is soft fringe so it may not matter.
- Not done: no 3D inflated surface for Fusion 360, no collapse simulation, no string path, no cuff-to-tube seal or air inlet detail. Laser bed size unknown (the cone strip is about 21 x 23 in). Needs a test cut and sew.

## Next
- Remy checks the flags and cuts a test on paper or cheap fabric.
- Then: a collapse and inflation simulation (reuse `../fabric-pattern/sim_polyp.py`), or the 3D surface output.

## History
- Round 1 (2026-11-15): first pattern, 3 pieces, folded ruffle, tight tip pitch 1.2.
- Round 2: looser tip pitch (2.0), cuff built into the strip (flared), fixed ruffle notches.
- Round 3: no allowance on the cuff's open end, straight seam for the last 2 in, 0.5 in alignment tabs, single-layer flared frill (starts 3 in up, cut in pieces).
- Round 4 (2026-11-16): the frill is one long straight strip with the free part slit into 0.25 in fringe (Remy: round 3 misread it, so the flared multi-piece frill and its curvature maths were removed); the cone comes to a point; fixed the tool's update button (see below).

## The tool's update button (fixed 2026-11-16)
The first version looked for `spiral_tool.py` in the wrong folder (it ran git from the polyp tool's folder), so Get latest changes always said "doesn't have the spiral-cone tool in it". Now it runs git from its own folder. The page also opens the newest version by itself: on load it checks GitHub, and if a newer branch that contains the tool (newest commit first) or newer commits exist it switches, pulls and reloads (tick box "Open the newest version automatically", on by default). It still refuses if local files were edited or there are unpushed commits. Tested here with a fake GitHub: the old code reproduces the error, the new code switches branch and restarts, and opening the page alone updates it. A Mac that still runs the old code needs the one-time paste in chat (re-running `install-mac.sh` restarts the tool), because the old button cannot update itself.
