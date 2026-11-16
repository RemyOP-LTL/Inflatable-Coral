# Cone worm pattern simulator: handoff (2026-11-16)

A stand-alone tool that turns a few numbers into the flat sewing and laser-cut pattern for a **spiral-cone polyp** (the "cone worm"): a long cone of woven nylon made from one spiral strip, with a fringed frill sewn into the spiral seam. It is separate from the 5-finger polyp tool (`polyps/fabric-pattern/`) and is not to be merged into it. Remy's decision, 2026-11-16: keep it as its own tool, and sort out sharing and updating later.

Everything is in this folder. It runs on its own: copy the folder anywhere.

## Run it (on your own computer, no cloud)
1. Python 3 with `pip install -r requirements.txt` (numpy, matplotlib, shapely).
2. The tool page: `python3 spiral_tool.py`. It opens http://127.0.0.1:8820/. Change a number, the pattern redraws in about two seconds. Ctrl+C stops it.
3. Or without the page: `python3 spiral_cone.py --out some-folder` writes `spiral-cone.svg`, `spiral-cone.png` and `spiral-cone.txt`. Change a setting with `CONE="LENGTH=12,PITCH_TIP=3" python3 spiral_cone.py --out some-folder`.
4. Outside the Coral repo, the page just has no "Get latest changes" card (it only works inside the Coral git repo). Ignore `install-mac.sh` and the auto-update; they belong to the cloud workflow you are leaving.

## What the design is (Remy's decisions)
- Woven nylon, no stretch, air inflates it, a motor winds one string to collapse it along its axis. The string anchors at the tip and runs straight down the axis.
- Why this shape: the 5-finger prototype did not work as hoped, and had too many pieces and seams in tight spaces. This one has **2 pieces** (3 with a separate cuff band) and a few long seams. Cutting is on a laser, so cut detail is free.
- **Cone strip:** one long curved strip, wound in a spiral and sewn edge to edge with the seams on the inside. The turns are closer together toward the tip (pitch 3 in at the base to 2 in near the end, both are settings), then the seam runs out into **one straight seam for the last 2 in**, and the cone **comes to a point**.
- **Cuff built into the strip:** the bottom 2 in of the strip is the cuff. 130 mm (5.12 in) across at the cuff line, so it slides over a 5 in (127 mm) tube. **No seam allowance on the open end of the cuff.** Limit: a straight tube cannot share one flat piece with a cone without stretching, so the cuff flares (5.12 in at the cuff line, 6.14 in at the open end). `CUFF_IN_STRIP=0` gives a separate straight cuff band instead.
- **Frill:** ONE long straight strip. Starts 3 in up the axis from the cuff line and runs to the end of the spiral seam (14.7 in long at the defaults). Single layer, not folded. Solid 0.5 in seam allowance along the sewn edge. The part that stands out (2.5 in) is slit into **0.25 in strands** by the laser, so it does not scrunch. Slits run from the sew line to the free edge.
- **Alignment tabs:** 0.5 in squares sticking out of the cut edges, to tack the pieces together before sewing. Numbered tabs on both edges of the cone strip and on the frill (tabs with the same number go together), and S1, S2 on the straight seam.
- Seam allowance 0.5 in everywhere except the open end of the cuff.

## Defaults (10 in cone above the cuff line)
Half angle 14.4 degrees. Spiral 3.4 turns including the cuff, 41.5 in of spiral seam, the frill covers the last 14.7 in of it, straight seam 2 in. Cone strip about 21 x 23 in (bounding box). Frill strip 14.7 x 3.0 in with 59 slits. 10 numbered tabs plus S1, S2.

## Files
- `spiral_cone.py`: all the maths and the drawing. Settings are at the top (every one is also a field in the tool). Writes SVG (true size, inches: red cut, blue dashed sew line, grey dotted cuff line), PNG (flat pieces and a 3D sketch), TXT (numbers and checks).
- `spiral_tool.py`: the browser page (port 8820). Fields for every setting, shows warnings, SVG download.
- `polyp-2026-11-15-spiral-cone/`: latest default outputs.
- `snapshot.html`: the page published as the results link (https://claude.ai/artifact/4QKZ6Q71NCG22exGFGVP4N).
- `CLAUDE.md`: working notes and history (written for the cloud sessions).
- `install-mac.sh`, the "Get latest changes" and auto-update code: cloud-workflow only, safe to delete.
- `requirements.txt`: numpy, matplotlib, shapely.

## How the maths works (so you can change it)
- A cone (even a cut-off one) unrolls flat with no stretching, like a paper party hat. A seam winding up the cone becomes a spiral curve on the flat fan.
- The seam goes round by theta(z) = 2 pi times the integral of dz / pitch(z). Over the last `TRANSITION` inches before the straight part, the winding rate fades to zero so the seam turns smoothly straight.
- The strip is the region between one turn of the seam and the next turn above it. It starts as a thin wedge at the open end of the cuff, and its two straight edges meet at the point at the top.
- The `PITCH_BASE` and `PITCH_TIP` settings are the rate at one exact height. The height actually gained across one full turn differs a little (2.82 in over the first turn at the defaults).
- Tabs are placed by arclength along the seam, counted from where the frill starts, so the cone's two edges and the frill agree. Slit positions divide the frill length evenly.
- Everything is in `flat()`, `Cone`, and `build()` in `spiral_cone.py`.

## Checks already done (defaults, 2026-11-16)
- The seam as the strip's bottom edge and as its top edge: 41.521 in both (so the two edges meet along the same seam).
- Open-end arc equals pi times its diameter (19.295 in). Apex exactly at one point. Straight edges 2.064 in each (2 in along the axis). Radius at the cuff line exactly 130 mm / 2. Frill strip length equals the seam it covers.
- Ran without errors for other lengths and diameters, an open tip, no straight part, a sharp corner (`TRANSITION=0`, which warns that tabs touch), the separate cuff band, and other frill widths.
- Not checked: nothing has been cut or sewn yet. The SVG has only been looked at as picture and parsed as valid XML, not opened in the laser software. The 3D picture is a sketch (the frill is drawn as straight lines), not a simulation.

## Assumed and not decided (confirm)
- **Frill width:** `RUFFLE_WIDTH` 3 in is the cut width, so 0.5 in solid allowance plus 2.5 in of fringe. If Remy meant 3 in of fringe, set 3.5.
- Frill start is measured from the cuff line (top of the cuff), not from the open end.
- Pitch 3 in and 2 in, fabric width 58 in, straight-seam blend 2 in, strand width 0.25 in (adjusted slightly so strands divide the length evenly), slits stop at the sew line.
- The frill stands at right angles to the cone surface.
- Laser bed size is unknown. The cone strip is about 21 x 23 in.

## Open flags
- The 2.5 in fringe is longer than the cone's radius (0.5 in) where the spiral ends, so fringe from opposite sides overlaps near the top. The tool warns. It is soft fringe, so it may not matter. A shorter frill or a larger tip fixes it.
- The flared cuff may not seal well. A separate straight band is one setting away.

## Not done yet
- Test cut and test sew (paper or cheap fabric first).
- The 3D surface of the inflated cone, for designing the motor and blower around it in Fusion 360. Nothing to export yet.
- Collapse simulation (does the spiral seam and frill let it shorten along its axis? how much string force?). The cloth simulation in `../fabric-pattern/sim_polyp.py` is the thing to adapt.
- The string path and tip anchor, the cuff-to-tube seal, and the air inlet.
- Whether a sewing machine can follow the spiral seam.
- Possibly a DXF export if the laser software prefers it to SVG.

## Mistakes along the way (so they are not repeated)
- Round 3 misread the frill, and built flared curved pieces in 3 parts with curvature maths. Remy wanted one straight strip with fringe. Removed in round 4.
- The tool's "Get latest changes" first looked in the wrong folder, so it always failed. Fixed, but it is only relevant to the cloud workflow.
- Ask before building when a description could be read two ways. The frill and the cuff were both ambiguous.

## History
- 2026-11-15: first pattern (3 pieces, folded ruffle). Looser tip pitch, cuff built into the strip, fixed notches. Cuff allowance removed, straight seam, 0.5 in tabs, single-layer frill (misread).
- 2026-11-16: frill as one fringed strip, cone to a point, update fix. Made stand-alone, this handoff written. Branch `polyp-2026-11-15-spiral-cone` on `RemyOP-LTL/Inflatable-Coral`. **Not merged and not to be merged.**
