# polyps/sea-anemone/

**Branch `polyp-2026-11-18-profile-editor` (2026-11-18): the tube's cross-section is now a 4-point spline you can edit in a cross-section view.** The older branch `polyp-2026-11-17-sea-anemone` still has the simple three-diameter (bottom / middle / top) tube. See "Tube cross-section spline" below.

## Purpose
A third polyp design, started 2026-11-17 on branch `polyp-2026-11-17-sea-anemone` (branched from the cone worm branch). Same approach and app features as the cone worm (`../spiral-cone/`, not changed): a flat-pattern generator plus a small Mac window app. Motion is NOT simulated (Remy, 2026-11-17: of limited value).

## The design (Remy, 2026-11-17)
- **Tube:** one piece, ONE straight seam, sewn on the inside. Tubular, slightly flared at the base and at the tip: three diameters (bottom, middle, top) and a height. Everything in millimetres, fabric width too.
- **Cap:** a flat disk that closes the top of the tube.
- **Frill:** one straight strip sewn into the ring seam between the tube top and the cap, same idea as the cone worm. Its sewn edge is V-notched so the straight strip can bend into a circle. The free part is slit into 6 mm strands (laser cut).
- **Frill notches:** about 9.5 mm (3/8 in) deep, leaving about 3 mm. Fallback if that is too weak: notch deeper and keep a solid, unslit band (setting `FRILL_BAND`, e.g. 6 mm = 1/4 in) between the sew line and the fringe.
- **Tube notches (updated 2026-11-17):** V notches about 6 mm deep on the tube seam allowances that remain (both side edges and the top edge) because they are all curved. Only the cap edge has none: it is meant to wrinkle when the piece is turned inside out, which adds texture (Remy).
- **Notch spacing is now a count between tabs**, not a distance: `TUBE_NOTCHES_BETWEEN_TABS` (default 3) and `FRILL_NOTCHES_BETWEEN_TABS` (default 7) = notches evenly spaced between each pair of neighbouring tabs. The old distance setting clashed with the tab positions. No notch goes in the corner where the side seam joins (or where the frill strip's ends meet), so with an even count the middle notch of that gap is left out.
- **No seam allowance on the bottom edge of the tube** (Remy, 2026-11-17). The bottom edge has no notches either.
- **Wavy, round-ended fringe (2026-11-17):** every fringe strand has a round tip and the slits are waves. `FRILL_WAVE` (slider in the app, mm of wave height, 0 = straight; releasing the slider rebuilds) and `FRILL_WAVE_LENGTH`. All slits are the same wave shifted sideways, so the strands nest exactly; the wave eases to zero at both ends of each strand so the tips are clean semicircles. The strip's two ends are the same wave, so they join into the ring. Strip is up to the wave height wider than the ring circumference at its ends. Defaults 3 mm / 40 mm are guesses.
- Adjustable (top of each card in the app): height, diameter bottom / middle / top, frill length (how far the fringe stands out; the strip's cut width is that plus the seam allowance and solid band), strip length round the ring (0 = fits the ring exactly).

## Tube cross-section spline (branch profile-editor, 2026-11-18)
- The tube's profile (radius against height) is a spline through 4 control points: bottom (height 0, bottom diameter), **lower** point, **upper** point, top (height = tube height, top diameter). Between neighbours it is a cubic Bezier (CAD-style): start, start + handle, end - handle, end.
- The lower and upper points each have: position (lower: height above the bottom + diameter; upper: distance below the top + diameter) and a tangent: **angle** in degrees from the tube's axis (0 = straight up the axis, + = widening going up, - = narrowing) and **length** (handle length in mm: how far the direction holds before the curve bends). The bottom and top points use a natural end: tangent along the line to their neighbour, handle a third as long.
- Settings: `LOWER_HEIGHT, LOWER_DIAMETER, LOWER_ANGLE, LOWER_LENGTH, UPPER_FROM_TOP, UPPER_DIAMETER, UPPER_ANGLE, UPPER_LENGTH`. `DIAMETER_MIDDLE` is gone (old snapshots simply lose that value). Defaults (60 / 135 mm / -5 deg / 35, mirrored on top) reproduce the old smooth shape to within 0.2 mm.
- Cross-section view (card above the pattern): drag a red dot to move that control point (height and diameter); drag a yellow square to set its tangent direction and length. The boxes on the left follow, and it rebuilds when you let go. Typing in the boxes redraws the view. The scale is true (equal mm both ways); the dashed line is the axis. The curve maths is the same in the page (JavaScript) and in `sea_anemone.py` (checked equal to 6 digits).
- The white bottom and top dots can be dragged in or out (diameter only; their heights stay fixed). Zoom in the flat-pattern preview is now only in the Laser cut view (removed from Detailed, Remy 2026-11-18).
- Errors: a handle so long or steep that the curve doubles back, middle points out of order or outside the tube, or a profile narrower than 20 mm, give a clear message.

## What's here
| File | Job |
|---|---|
| `sea_anemone.py` | The pattern maths and all outputs (settings are module variables at the top). `build()`, `export_items()`, `write_svg/pdf/dxf`, `draw_png*`, `report()`. Run alone: `python3 sea_anemone.py --out folder`; override with `ANEMONE="HEIGHT=300,DIAMETER_TOP=170"`. |
| `anemone_3d.py` | The right-hand picture of the finished, inflated anemone (see below). Drawn by hand with a depth-sorted painter, because matplotlib's own 3D mixes up what is in front when surfaces and ribbons overlap. |
| `anemone_tool.py` | Local web server and the page (`FIELDS` lists every input box). Port **8830** (window app picks the first free of 8830-8839). Same sticky Rebuild / snapshot tile, Detailed / Laser cut switch, Save PDF / DXF / SVG (asks where, via the Mac Save window), Refresh tool button as the cone worm. |
| `anemone_window.py` | The Mac window (pywebview), starts the server and restarts it if it dies. |
| `install-app.sh` | One-time setup: `.venv`, libraries, builds `~/Applications/Sea Anemone.app`. |
| `icon/` | Logo (SVG, PNG, icns). |

## How the flat tube is found
The profile is a smooth curve (quadratic) through the three diameters. A smooth hourglass cannot unroll flat without distortion. We keep the line opposite the seam straight and true length, make each ring an arc of its true circumference, and bend those arcs by a fraction of the true curvature. That fraction is solved so the flat side edge is exactly as long as the tube's surface line. A plain cone (all three diameters on a straight line) comes out exact. The distortion lands on the in-between lines. If the edge cannot match (a bulge: middle wider than the ends) the report shows the difference.

## Previews in the app (2026-11-17)
- Dark background previews (exports for the laser are unchanged: white page, black lines). The flat-pattern preview is a vector SVG (`preview-detailed.svg`, `preview-outline.svg`) that can be zoomed: scroll wheel, +/- buttons, drag to move, double-click or Fit to reset. Lines keep their thickness when zoomed. The zoom resets when switching between Detailed and Laser cut.
- The inflated picture (`picture-3d.png`) is all white on the dark background and shows under the Detailed view only.

## The 3D picture (2026-11-17, a drawing, not a physics simulation, no motion)
- (Updated 2026-11-18, Remy) The top diameter is fixed: the seam ring is held at 96% of the top diameter setting (`K_TOP` in `anemone_3d.py`) and does not collapse further, so the top keeps its shape and the cap pouches out less. The cap is a shallow spherical dome whose fabric (seam to centre) is exactly the cap radius (about 18 mm high at the defaults). The tube wall follows the pattern's radius, eases in to the seam ring over 14 mm, and the seam height is solved so the tube fabric equals the flat pattern's side-edge length. The ring is 4% smaller than the tube top, so a little fabric gathers: wrinkles are drawn round the seam (decoration).
- Frill: one ribbon per strand, leaving the seam going outward and blown upward by air from the base. Each strand keeps its real length (the frill length) and the pattern's wave; direction is random but trends up (about 52 degrees on average, spread by a smooth random pattern round the ring plus per-strand noise; fixed random seed so it does not change on every rebuild).
- Not done: no real inflation or cloth simulation; the dome height and corner roundness come from the length rules above, not from pressure. The wrinkles are decoration.

## Checked (2026-11-17, defaults: height 250, diameters 150 / 130 / 150)
- Flat side edge 251 mm = surface line 251 mm. Circumferences 471 / 408 / 471 mm. Tube cut size 510 x 287 mm, cap 174 mm across, frill 471 x 60 mm (79 strands of 6 mm, 78 slits of 48 mm), 3 pieces.
- DXF read back with ezdxf: units mm, layer CUT only on the laser file, 3 closed loops, sizes match the report. PDF read back with pymupdf: 3 paths, all black 0.072 pt (0.001 in), no fill, no text. The frill loop is not a "valid" polygon only because the slits are doubled lines, as intended.
- Odd settings run (bulge, long frill, band, no notches, strong taper); too-narrow settings give a clear error.

## Assumed, not decided (confirm with Remy)
- Defaults: bottom and top 150 mm, middle 130 mm; frill width 60 mm; seam allowance 12 mm on every edge except the tube's bottom edge (none); fabric 1470 mm; tabs 12 mm every 125 mm.
- The profile is a quadratic through the three diameters (smooth, no straight middle section).
- Frill length 0 = exactly the top circumference (pi x top diameter). A longer strip gathers, a shorter one leaves a gap (the tool warns).
- Frill notch width is worked out from the circle (each notch takes out its share of the extra allowance length), not a fixed angle. Tube notches use a fixed 50 degree V like the cone worm. Default counts (3 and 7) are guesses.
- No notches on the cap disk edge (on purpose, see above).
- The two ends of the frill strip are left to be joined by hand (no extra allowance for an end seam).
- Ring tabs: lettered A, B, ... on the tube top edge, cap and frill; side seam tabs numbered 1, 2, ...

## Not done / not verified
- Not run as the real Mac app (`install-app.sh` not run; the window and the Mac Save dialog are untested). Tool checked in a browser on a spare port.
- No test cut or sew. Laser bed size and fabric still open.
- No 3D surface for Fusion 360 (deferred, as for the whole project).

## Next
- (2026-11-18) Remy is sewing a real sample and will send a photo. Then rework the 3D picture / simulation of the inflated shape against it (dome height, corner roundness, how the tube and gathers really sit, how the frill really hangs). Useful to note with the photo: settings used (a saved snapshot name), fabric, whether it was inflated, and any measurements (height, widest diameter, dome height).
- Remy runs `./install-app.sh` here, opens Sea Anemone, tries a test cut on paper or cheap fabric.
- Settle notch depths and the frill band from the test sew.
