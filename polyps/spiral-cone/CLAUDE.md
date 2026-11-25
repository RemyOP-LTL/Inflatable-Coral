# polyps/spiral-cone/

**Latest state (2026-11-17): the app moved on a lot since this file was first written (metric, Mac window, snapshots, PDF/DXF laser exports, notches). Start with `NEXT-SHAPE-BRIEF.md` for the current feature list and file map; Remy is starting a separate app for a new shape.**

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

## Mac window app (2026-11-16)
- **Cone Worm.app** (in `~/Applications`, Christmas tree worm icon) opens the tool in its own window via `cone_window.py` (pywebview), same pattern as the skin's Coral Frame Tool. It starts `spiral_tool.py` in the background, restarts it if it dies, stops it when the window closes. Ports 8820-8829 (first free one; 8820 was taken by an older copy running from `~/coral-simulator`, so it uses 8821).
- One-time setup: `./install-app.sh` in this folder (makes `.venv`, installs `requirements.txt` incl. pywebview, builds the app). Log: `~/Library/Logs/cone-worm.log`.
- **Refresh tool** button in the top bar (replaces the old "Get latest changes" card and the branch-switching code): git fetch, fast-forward only if safe, pip install, restart in place, page reloads. The top bar shows branch, date, last commit message, "edited here" if uncommitted. Tested: server restarted and the page reloaded.
- Sizing inputs are plain number boxes with the unit after; nothing recalculates while typing; **Rebuild** applies everything, and "Sizing changed. Press Rebuild." shows after an edit. Tested in the browser pane (LENGTH 10 -> 12 changed the numbers).
- Logo: `icon/cone-worm-logo.svg` (source), `.png`, `cone-worm.icns` (two spiral crowns on coral).
- `~/cone-worm` is now a real git clone (branch `polyp-2026-11-15-spiral-cone`). The earlier plain copy is at `~/cone-worm-plain-copy` (safe to delete).
- Not tested: that the window shows on your screen (the process started and the server answered, but I could not see the window); first launch may need right-click > Open.
- Not done: `START-HERE.md` (not on this branch), commit/push (nothing committed yet), test cut and sew, the open flags above.

## Metric and input sections (2026-11-16)
- **Everything is millimetres now**: settings, the numbers file, the PNG axes and the SVG (width/height in mm, 1 drawing unit = 1 mm, 50 mm test square instead of the 1 in one). Old inch values are not accepted any more (the `CONE=` override is mm too).
- Defaults were rounded to tidy metric numbers, so the design moved a little: length 250 (was 254), pitch 75 / 50 (was 76.2 / 50.8), straight seam and blend 50, seam allowance 12 (12.7), frill width 75 and start 75 (76.2), cuff 50, fabric 1470, tabs 12 mm every 125, fringe 6 mm (6.35, so 62 strands not 59). Check that the maths is unchanged: with the exact old values converted (254, 76.2, ...) the new code gives the same seam length, strip size, turns and tab count as the inch version.
- Page inputs are in four sections: **Cone shape** (length, cuff line diameter, tip diameter, cuff height, cuff in strip), **Seam** (pitch base/end/curve, straight seam length, blend, seam allowance, fabric width), **Frill** (start, strip width, fringe width), **Tabs** (size, spacing). No descriptions. Rebuild / reset sit in a sticky box at the top of the column.
- Hard-coded small numbers in `spiral_cone.py` (tab clearance, edge sampling, layout gaps, SVG line widths, fonts) were converted to mm as well.

## Round 6 page changes (2026-11-16)
- Fabric width is the one setting in **inches** (default 58 in); converted to mm before the pattern runs. Flat-pattern PNG shows mm (bottom/left) and inches (top/right).
- Page no longer shows the settings list (it stays in the `.txt` file) or the design warnings at the top of the Pattern tile (only rebuild errors show there; the "Checks" list is still at the end of the numbers).
- Rebuild is greyed out when the boxes match what was last built. No "Sizing changed" banner.
- "Cuff in the strip" became **Separate cuff** (No/Yes switch; Yes = `CUFF_IN_STRIP=0`).
- New setting **Frill ends at (distance from tip)**, `FRILL_END_FROM_TIP`, mm along the axis. Interpretation (confirm with Remy): it sets where the frill ENDS, measured from the tip; the start is still measured from the cuff line. Default 50 = the straight-seam length, so the default pattern is unchanged. It cannot be smaller than the straight seam length (the frill does not run along the straight seam) and the frill must be at least 12 mm long.
- **Snapshots**: the sticky top tile has a name box + Save and a "Load a snapshot..." menu. Saved as small JSON files in `snapshots/` (git-ignored, so not backed up on GitHub). Same name overwrites. Loading fills the boxes and rebuilds.
- The sticky tile (Rebuild, reset, save, load) is meant to be reused in the other tools.

## DXF export and forced snapshot naming (2026-11-15)
- New `<name>.dxf` from `spiral_cone.py`: ONLY the cut outlines of the cone strip and the frill (frill slits on layer SLITS, outlines on layer CUT, both red). No sew lines, labels or cuff band. Plain ASCII DXF (R12 style), no extra library. Units are millimetres (`$INSUNITS` 4), true size, y up; the cone sits at (0,0) and the frill is 50 mm below it.
- Checked with an independent reader (ezdxf in a scratch venv): units = mm, cone 514.9 x 570.6 mm and frill 372.0 x 87.0 mm (75 mm strip + 12 mm tabs) match the report, areas match the SVG exactly, 61 slits of 63 mm = the fringe length.
- Page: DXF and SVG download links now open a small "Name this snapshot" box; a name is required, the BUILT values are saved as a snapshot, then the file downloads. Names: `<snapshot>_cone-and-frill-outline_mm.dxf` and `<snapshot>_pattern_mm.svg` (spaces become `_`).
- `cone_window.py` now sets `webview.settings["ALLOW_DOWNLOADS"] = True`. Without it the Mac window ignored download links, so the old SVG link did nothing in the app. Not tested inside the real window (tested in the browser pane on a spare port).
- Open: the separate cuff band is not in the DXF (only "frill and spiral" were asked for); say if it should be.

## Laser cut view and PDF export (2026-11-17)
- The pattern tile has a Detailed / Laser cut switch. Detailed = the old picture (flat pieces with sew lines, cuff line, numbered tabs, plus the 3D sketch). Laser cut = flat pieces only, cut lines only (preview has mm and inch axes).
- Downloads (PDF, DXF, SVG) export whatever view is showing, with no scales, grid or test square. Names: `<snapshot>_detailed_mm.pdf` and `<snapshot>_outline_mm.pdf` (same for .dxf/.svg; changed 2026-11-17 from view-first). The first download of a new config forces naming and saving a snapshot; later downloads of the same built settings (other format or view) reuse that name with no question. Loading or saving a snapshot also counts as naming those settings. Changing and rebuilding the settings asks again.
- Files made per build (`spiral_cone.py`): `-detailed.{pdf,svg,dxf}`, `-outline.{pdf,svg,dxf}`, `.png`, `-outline.png`. Shared item list: `export_items()`.
- PDF page = exactly the drawing plus 10 mm margin, 1 pt = 1/72 in (true size, no scaling needed). Outline PDF is red 0.1 pt hairlines only, no background rectangle, no text. Detailed PDF/DXF include labels and titles; detailed DXF layers: CUT, SLITS, SEW, MARK, LABELS, TITLES.
- Each fringe slit is ONE line (61 lines of 63 mm in the default pattern, checked by reading the PDF and DXF back). Outlines are closed shapes. If the laser still shows doubled slit lines, tell Claude what the cutter software shows.
- The separate cuff band (when on) is now included in all exports, DXF too (earlier DXF left it out).
- Checked: PDF page 534.9 x 727.6 mm = SVG size; drawn extent 514.9 x 707.6 mm; cone width matches the report. Not tested in the real Mac window.
- (2026-11-17) Exports no longer use a browser download (the Mac window navigated to a PDF preview with no way back). Now `POST /api/export` copies the file into `~/Downloads` as `<snapshot>_<view>_mm.<ext>` (overwrites the same name) and the page shows "Saved <file> in your Downloads folder. Show in Finder" in place (`/api/reveal` runs `open -R`). Links are now "Save PDF / DXF / SVG". Tested in the browser pane, not in the real window.
- (2026-11-17) Laser PDF (`-outline.pdf`) lines are pure black, 0.001 in wide (0.072 pt), checked by reading the PDF back (63 paths, all black, 0.001 in). Detailed PDF keeps its colours. Saving now asks where: `ask_save_path()` in `spiral_tool.py` opens the Mac Save window through `osascript` (starts in the last folder used, kept in `snapshots/.last-save-folder`; first time Downloads); Cancel saves nothing. The stubbed save path was tested in the browser pane; the real Save window was started and cancelled from the shell but not seen on screen, so it may open behind other windows (not verified).

## Notches and one-loop frill (2026-11-17)
- Seam allowance notches: V notches (50 degrees) cut into the allowance along the two curved cone edges, spacing blends from NOTCH_SPACING_BASE (60 mm) at the cuff end to NOTCH_SPACING_TIP (20 mm) at the tip end of the spiral, by distance along the seam. NOTCH_DEPTH 8 mm (kept at least 2 mm short of the sew line; 0 = none). Skipped near alignment tabs and within 15 mm of either end of the seam. Not on the straight seam (radial edges, no curvature mismatch). All three numbers are ASSUMED from Remy's prototype note, not tested on fabric. Default pattern: 42 notches.
- Frill exports are now ONE closed loop per piece (the laser cutter did not like separate slit lines): the loop walks down each slit and back up along the free edge, so slits are doubled lines. The SLITS layer in the DXF is no longer used. Outline PDF now has 2 paths (cone, frill), all black 0.001 in.
- Checked by reading the PDF/DXF back (2 closed entities, CUT layer only) and looking at the rendered outline. Not yet cut on the real laser.

## Frill and notches ported from the sea anemone tool (2026-11-24)
Source: `polyps/sea-anemone/` (branch `polyp-2026-11-18-stacked-cones`, Remy's sea anemone thread). Read only, nothing changed there.
- **Sacrificial strip on the frill:** a thin strip (`SACRIFICE_STRIP_WIDTH` 2 mm, 0 = none) runs across the free ends of all fringe strands, joined to each strand tip by a bridge (`SACRIFICE_CONNECTOR_WIDTH` 1.5 mm, `SACRIFICE_CONNECTOR_LENGTH` 1.5 mm); cut it off after sewing. The frill is now one outer outline plus ONE CLOSED LOOP PER GAP between neighbouring bridges (61 at the defaults) instead of the one doubled-back loop. With the strip set to 0 the old single doubled-back loop is used (now with round tips).
- **Wavy, round-ended fringe:** every strand has a round tip; `FRILL_WAVE` 3 mm and `FRILL_WAVE_LENGTH` 40 mm (the anemone defaults, ASSUMED; 0 = straight slits). All slits are the same wave shifted sideways so strands nest; the wave eases to zero at both ends of each strand. The strip's two ends are wavy too.
- **Notches spread evenly between the tabs** (like the anemone's "count between tabs"), not by raw distance: each gap between neighbouring tabs is cut into equal parts of about NOTCH_SPACING (60 mm at the base blending to 20 mm at the tip end, so they still close up toward the tip). No notch lands on a tab. Depth now 6 mm (Remy's anemone value; was 8).
- **Corner notch:** the notch at the end of the spiral edges, where it meets the straight seam, is cut right on the corner as an open V (straight-sided slot past the allowance) on both edges; the two halves join into one notch when the straight seam is sewn. Its direction is taken 4 mm back along the edge, because the in/out test is unreliable exactly on a corner (taking it from the strip's centre cut a slot into the piece).
- The frill's seam allowance stays plain (no notches), as in the anemone. NOT ported: frill hoop-loop tabs (`FRILL_TAB_LENGTH`), solid band (`FRILL_BAND`), string-guide tabs, air holes, cap, nesting, laser bed.
- Checked: default build runs, outline PDF has 63 black 0.001 in paths (cone + frill outline + 61 gap loops) with no fill or text, DXF has 63 closed entities on layer CUT with every gap loop inside the frill outline, 41 notches, cut outline is one clean polygon. Tool page builds with the new fields (strip off and a too-wide bridge give the expected result/error). Not cut on the laser.

## 3D picture in the sea anemone style (2026-11-25)
- New `cone_3d.py` (adapted from `polyps/sea-anemone/anemone_3d.py`, read only): white shaded fabric on the dark background (`#1c1b1a`), drawn by hand with a depth-sorted painter (matplotlib's own 3D mixes up what is in front). Written as `<name>-3d.png`, shown in a dark box under the flat pattern in the Detailed view only (hidden in Laser cut), like the anemone. The old matplotlib 3D sketch next to the flat pattern is gone, so `<name>.png` is now the flat pattern only.
- It shows: the cone at the pattern's radius (cuff flared when it is part of the strip, a straight band with a darker ring when separate); the spiral seam as a continuous darker line (width measured across the slanted seam), tighter toward the tip, straight at the end; one frill strand per strand width along the seam between the frill start and end, leaving the seam outward and blown upward with random spread (fixed seed), the pattern's wave, real strand length. The tip is rounded a little.
- A drawing, not a simulation. Strand angles (about 46 degrees on average) are copied from the anemone and not tuned to a real sample.
