# polyps/spiral-cone/

## Purpose
A second polyp design, started 2026-11-15 on branch `polyp-2026-11-15-spiral-cone`. It sits beside the 5-finger design in `../fabric-pattern/` (not changed). Remy's 5-finger prototype did not work as hoped and had too many pieces and seams in tight spaces to sew at the scale of dozens of polyps. Cutting is not the problem (laser).

## The design (Remy, 2026-11-15)
- A long cone made from ONE long strip of woven nylon wound in a spiral (like a barber pole) and sewn edge to edge, seams on the inside. The cone shape comes from the strip tapering.
- Tighter wind toward the tip: turns closer together near the tip. Not too tight (the tip pitch was loosened to 2 in).
- **Cuff built into the strip** (2 in tall, 130 mm = 5.12 in across at the cuff line, which slides over the 5 in = 127 mm tube). **No seam allowance on the open end of the cuff** (removed 2026-11-15, it made an "ear" on the flat pattern).
- **Finish:** the spiral seam turns into one straight seam for the last 2 in of the cone length (smooth blend over `TRANSITION`, default 2 in).
- **Frill:** starts 3 in up the axis (from the cuff line) and runs to the end of the spiral seam. Single layer, 0.5 in seam allowance on the sewn edge only, not folded. It is laser cut with its flare built in so a non-stretching fabric does not scrunch.
- **Alignment tabs:** 0.5 in squares sticking out of the cut edges, at matching places on both cone edges and the frill (numbered 1..n), and on the straight seam (S1, S2). Remy tacks them together before sewing.
- Length about 10 in, base diameter and length are variables. Air enters through the cuff (a stitch seal is enough). Motion: collapses along its axis; one string anchored at the tip, straight down the axis.

## What's here
- `spiral_cone.py`: makes the flat pattern from settings. Writes `<name>.svg` (true size, inches, laser: red cut, blue sew, grey dotted cuff line), `<name>.png` (flat pieces and a 3D sketch), `<name>.txt` (numbers and checks). `python3 spiral_cone.py --out folder`; change settings with `CONE="LENGTH=12,PITCH_TIP=3" python3 ...`. Needs numpy, matplotlib, shapely only.
- `spiral_tool.py`: browser page with a field for every setting, port **8820** (http://127.0.0.1:8820/), with the same Version card and Get latest changes button as the polyp tool. `install-mac.sh`: one-time Mac setup (launchd agent `com.coral.spiraltool`). Tested here in a headless browser and with the Mac-only commands stubbed; not run on a real Mac yet.
- `polyp-2026-11-15-spiral-cone/`: the latest outputs, default settings. `snapshot.html`: the link page for Remy.
- It does not use the cloth simulation. `spiral_tool.py` imports `polyp_tool.py` from `../fabric-pattern/` for its git/version helpers, so both folders must be present.

## How the geometry works
A cone unrolls flat exactly, like a paper party hat. A seam winding up the cone becomes a spiral curve on the flat fan. The seam goes round theta(z) = 2 pi * integral of dz / pitch(z); over the last `TRANSITION` inches before the straight part the winding rate fades to zero, so the seam turns smoothly straight. The strip is the region between one turn of the seam and the next turn above it, starting as a thin wedge at the open end of the cuff and ending at the straight seam: its top edge on the last turn is the tip opening (one full turn), and the two straight edges are the two radial edges that meet in the straight seam.

The frill stands out at right angles to the cone surface. Flattening a strip around a curve gives a strip around a plane curve whose curvature is the cone's normal curvature along the seam, kappa = cos(half angle) cos^2(psi) / r (psi = angle between the seam and the circumference). The seam side is the inner edge (with the allowance) and the free edge is longer. The frill winds through more than 360 degrees in total, so it is cut in pieces (each at most `MAX_FRILL_TURN` degrees, more pieces automatically if one would overlap itself), with the ends of the pieces placed halfway between tabs.

## Checked (2026-11-15, defaults)
Seam edge lengths bottom and top: 44.274 in both. Open-end arc 18.667 in = pi x its diameter. Tip arc 3.142 in = pi x tip diameter. Straight edges 2.042 in each (2 in rise along the axis, 2.04 along the surface). Radius at the cuff line exactly 130 mm / 2. Frill sewn edge 17.147 in vs seam 17.148 in. The flat frill's free edge is 41.7 in, the true 3D free edge (the seam pushed out 2.5 in along the cone's normal) is 42.6 in, so the frill is about 2 % short on its free edge: the surface a normal-standing frill sweeps out is not exactly flattenable, and this is the closest flat shape. Expect a slight pull on that edge. Settings ran without errors for other lengths and diameters, no straight part, a sharp corner (`TRANSITION=0`, which warns about touching tabs), the separate cuff band and other frill widths.

## Defaults and results (2026-11-15, third round)
10 in cone above the cuff line, 130 mm cuff line, 1 in tip, pitch 3 in at the base to 2 in at the end of the spiral, spiral 3.4 turns (cuff included), spiral seam 44.3 in, frill on the last 17.1 in of it, straight seam 2 in. Cone strip bounding box 24.1 x 26.7 in. Frill: 3 pieces, each about 8 x 5 in, stands out 2.5 in. 11 numbered tabs plus S1, S2. 4 pieces to cut. A flared cuff: 5.12 in at the cuff line, 5.94 in at the open end (a straight ring cannot share a flat piece with the cone without stretching; `CUFF_IN_STRIP=0` gives a separate straight band).

## Assumed, not decided (confirm with Remy)
- Frill strip: `RUFFLE_WIDTH` = 3 in cut width = 0.5 in allowance + 2.5 in standing out. (If the 3 in is the part standing out, set 3.5.)
- Frill start is measured from the cuff line (the top of the cuff) along the axis.
- Tip diameter 1 in; pitch 3 and 2 in; fabric width 58 in; the straight seam blends in over 2 in (set `TRANSITION=0` for a sharp corner).
- Neighbouring frill pieces just butt together along their ends, they are not sewn to each other.
- The frill stands at right angles to the cone surface.

## Open flags
- The 2.5 in frill is taller than the cone's radius (0.91 in) where the spiral ends, so frill from opposite sides pushes into each other there. The tool warns. A narrower frill or a wider tip fixes it.
- Not done: no 3D inflated surface for Fusion 360, no collapse simulation, no string path, no cuff-to-tube seal or air inlet detail. Laser bed size unknown (the cone strip is about 24 x 27 in). Whether a machine can follow the spiral, and whether the frill pieces behave, needs a test sew.

## Next
- Remy checks the flags and cuts a test on paper or cheap fabric.
- Then: a collapse and inflation simulation (reuse `../fabric-pattern/sim_polyp.py`), or the 3D surface output.

## History
- Round 1 (2026-11-15): first pattern, 3 pieces, folded ruffle, tight tip pitch 1.2.
- Round 2: looser tip pitch (2.0), cuff built into the strip (flared), fixed ruffle notches.
- Round 3: no allowance on the cuff's open end, straight seam for the last 2 in, 0.5 in alignment tabs, single-layer flared frill (starts 3 in up, cut in pieces).
