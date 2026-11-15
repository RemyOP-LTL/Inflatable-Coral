# polyps/spiral-cone/

## Purpose
A second polyp design, started 2026-11-15 on branch `polyp-2026-11-15-spiral-cone`. It sits beside the 5-finger design in `../fabric-pattern/` (which is not changed). Remy's 5-finger prototype did not work as hoped, and it had too many pieces and too many seams in tight spaces to sew at the scale of dozens of polyps. Cutting is not the problem (laser).

## The design (Remy, 2026-11-15)
- A long cone made from ONE long strip of woven nylon wound in a spiral (like a barber pole) and sewn edge to edge. The cone shape comes from the strip tapering.
- Tighter wind at the tip: the turns sit closer together near the tip than at the base.
- Seams on the inside. A second strip, about 3 in wide with 1/2 in seam allowance, is sewn into the spiral seam and stands out on the outside as a spiral ruffle (fin).
- Cuff at the bottom, about 2 in tall, about 5 in across. Base is 130 mm (5.12 in) across, so the cuff is the same size and slides over a 5 in (127 mm) tube. Air enters through the cuff; a stitch seal is enough.
- Length about 10 in to start. Length and base diameter must be variables to play with.
- Motion: it collapses along its axis. One string, attached at the tip, runs straight down the axis.
- Pieces: 2 with the cuff built into the cone strip (default since 2026-11-15, Remy asked), or 3 with a separate cuff band (`CUFF_IN_STRIP=0`).

## What's here
- `spiral_cone.py`: makes the flat pattern from settings. Writes `<name>.svg` (true-size cut and sew lines, inches, for the laser), `<name>.png` (flat pieces and a 3D sketch) and `<name>.txt` (numbers and checks). `python3 spiral_cone.py --out folder`; change settings with `CONE="LENGTH=12,PITCH_TIP=0.9" python3 ...`. Needs numpy, matplotlib, shapely only.
- `spiral_tool.py`: browser page with fields for every setting, port **8820** (http://127.0.0.1:8820/), with the same Version card and Get latest changes button as the polyp tool. `install-mac.sh`: one-time setup on the Mac so it runs all the time (launchd agent `com.coral.spiraltool`). Tested here in a headless browser on Linux; not run on a Mac yet.
- `polyp-2026-11-15-spiral-cone/`: the first outputs, default settings.
- It does not import the cloth simulation. This step needed none (see below). `spiral_tool.py` does import `polyp_tool.py` from `../fabric-pattern/` for its git/version helpers, so both folders must be present.

## How the geometry works
A cone unrolls flat exactly, like a paper party hat. A seam that winds up the cone becomes a spiral curve on that flat fan. The seam height at angle theta is Q(theta), found from dQ/dtheta = pitch(Q) / (2 pi), with the pitch changing linearly with height (`PITCH_BASE` to `PITCH_TIP`, bent by `PITCH_CURVE`). The strip is what lies between one turn of the seam and the next turn above it, cut off at the base and tip circles. So the strip starts as a thin wedge at the base (its edge along the base circle for exactly one turn, the cuff seam) and ends as a thin wedge at the tip (the tip opening, also exactly one turn). Cut line = sew line plus `SEAM` all round.

Checked (2026-11-15): the seam is the same length as the strip's bottom and top edge (45.169 in both, so the ruffle fits both sides), the base edge equals pi x base diameter (16.079 in) and the tip edge equals pi x tip diameter (3.142 in).

## Updates 2026-11-15 (second round, Remy)
- Pitch made less tight: the tip pitch default is now 2.0 in (was 1.2). Base pitch 3.0 in. Both are sliders.
- **Cuff built into the strip** (`CUFF_IN_STRIP=1`, default). The strip simply starts `CUFF_HEIGHT` lower. The seam continues through the cuff as a plain seam, the ruffle starts at the cuff line (grey dotted line, notch 0). Limit found: a straight tube cannot be joined to a cone in one flat piece without stretching. The cuff-to-cone circle is a different curve flat on each side (the cuff would need about 8 % more length on its open edge). So the cuff here is the cone carried on downward: 130 mm (5.12 in) across at the cuff line, which is the tube fit, and 5.94 in at the open end. The cuff is not a straight ring. For a straight cuff, use `CUFF_IN_STRIP=0` (separate band, 3 pieces). The 130 mm is now the diameter at the cuff line, the top of the cuff.
- Verified again: seam edges equal (50.470 in both), open-end arc equals pi x its diameter (18.667 in), tip arc equals pi x tip diameter, radius at the cuff line is exactly 130 mm / 2.
- Fixed a bug: the ruffle strip's notches were piled at one end. They now sit every `TICK` inches of seam, notch 0 at the cuff line.
- The Mac setup script was tested here with launchctl and open replaced by stubs (environment built, agent file correct, tool starts from the new environment and answers). Still not run on a real Mac.

## Defaults and results, first round (10 in long, 130 mm base, 1 in tip, pitch 3 to 1.2 in, separate cuff band)
- Half angle 11.6 degrees, 5.1 turns of seam, 45.2 in of seam. Cone strip cut size about 20 x 23 in (bounding box). Ruffle strip 3 x 46 in. Cuff band 17.1 x 3.5 in.
- The pitch settings are the rate at that exact height. The height actually gained across one full turn is a little less near the base (2.75 in against 3.0) and more at the tip (1.31 against 1.2). The report shows both.
- Fin height is (ruffle width - 2 x seam) / 2 = 1.0 in. It is taller than the 0.5 in tip radius and about as tall as the tightest pitch, so the tool warns that fins will crowd near the tip.

## Current defaults (2026-11-15 second round): 2 pieces, cone strip bounding box 24.1 x 26.9 in, ruffle strip 3 x 39.7 in, 38.7 in of seam above the cuff line (50.5 in with the cuff part), 4.7 turns, pitch 3 to 2 in.

## Assumed, not decided (confirm with Remy)
- Tip diameter 1 in; pitch 3 in at the base and 2 in at the tip; ruffle fullness 1 (not gathered); fabric width 58 in.
- Ruffle strip is folded in half lengthwise, both raw edges in the spiral seam (three layers: cone edge, folded ruffle, cone edge), so a 3 in strip with 1/2 in allowance gives a 1 in fin. If Remy means a single layer that stands out 2 in or more, change `RUFFLE_WIDTH` or the fold logic.
- The 3D sketch only draws fin direction (straight out). It does not simulate fabric, air or collapse.

## Not done yet
- No 3D inflated surface for Fusion 360, no simulation of collapse along the axis (does the ruffle seam let it telescope? how much force does the string need?), no string path, no cuff-to-tube seal or air inlet detail, no gathered ruffle.
- Laser bed size unknown (the cone strip is about 20 x 23 in; the ruffle is 46 in long and could be cut in pieces).
- The strip is one piece sewn once around 5 turns. Sewing order, and whether a machine can follow the spiral, needs a test sew.

## Next
- Remy checks the assumptions above and a test cut on paper or cheap fabric.
- Then: a collapse and inflation simulation (reuse `../fabric-pattern/sim_polyp.py`), or the 3D surface output.
