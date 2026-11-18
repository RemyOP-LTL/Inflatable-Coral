# polyps/sea-anemone/

## Purpose
A third polyp design, started 2026-11-17 on branch `polyp-2026-11-17-sea-anemone` (branched from the cone worm branch). Same approach and app features as the cone worm (`../spiral-cone/`, not changed): a flat-pattern generator plus a small Mac window app. Motion is NOT simulated (Remy, 2026-11-17: of limited value).

## The design (Remy, 2026-11-17)
- **Tube:** one piece, ONE straight seam, sewn on the inside. Tubular, slightly flared at the base and at the tip: three diameters (bottom, middle, top) and a height. Everything in millimetres, fabric width too.
- **Cap:** a flat disk that closes the top of the tube.
- **Frill:** one straight strip sewn into the ring seam between the tube top and the cap, same idea as the cone worm. Its sewn edge is V-notched so the straight strip can bend into a circle. The free part is slit into 6 mm strands (laser cut).
- **Frill notches:** about 9.5 mm (3/8 in) deep, leaving about 3 mm. Fallback if that is too weak: notch deeper and keep a solid, unslit band (setting `FRILL_BAND`, e.g. 6 mm = 1/4 in) between the sew line and the fringe.
- **Tube notches:** V notches about 6 mm deep along both curved side edges.
- Adjustable (top of each card in the app): height, diameter bottom / middle / top, frill length, frill width.

## What's here
| File | Job |
|---|---|
| `sea_anemone.py` | The pattern maths and all outputs (settings are module variables at the top). `build()`, `export_items()`, `write_svg/pdf/dxf`, `draw_png*`, `report()`. Run alone: `python3 sea_anemone.py --out folder`; override with `ANEMONE="HEIGHT=300,DIAMETER_TOP=170"`. |
| `anemone_tool.py` | Local web server and the page (`FIELDS` lists every input box). Port **8830** (window app picks the first free of 8830-8839). Same sticky Rebuild / snapshot tile, Detailed / Laser cut switch, Save PDF / DXF / SVG (asks where, via the Mac Save window), Refresh tool button as the cone worm. |
| `anemone_window.py` | The Mac window (pywebview), starts the server and restarts it if it dies. |
| `install-app.sh` | One-time setup: `.venv`, libraries, builds `~/Applications/Sea Anemone.app`. |
| `icon/` | Logo (SVG, PNG, icns). |

## How the flat tube is found
The profile is a smooth curve (quadratic) through the three diameters. A smooth hourglass cannot unroll flat without distortion. We keep the line opposite the seam straight and true length, make each ring an arc of its true circumference, and bend those arcs by a fraction of the true curvature. That fraction is solved so the flat side edge is exactly as long as the tube's surface line. A plain cone (all three diameters on a straight line) comes out exact. The distortion lands on the in-between lines. If the edge cannot match (a bulge: middle wider than the ends) the report shows the difference.

## Checked (2026-11-17, defaults: height 250, diameters 150 / 130 / 150)
- Flat side edge 251 mm = surface line 251 mm. Circumferences 471 / 408 / 471 mm. Tube cut size 510 x 287 mm, cap 174 mm across, frill 471 x 60 mm (79 strands of 6 mm, 78 slits of 48 mm), 3 pieces.
- DXF read back with ezdxf: units mm, layer CUT only on the laser file, 3 closed loops, sizes match the report. PDF read back with pymupdf: 3 paths, all black 0.072 pt (0.001 in), no fill, no text. The frill loop is not a "valid" polygon only because the slits are doubled lines, as intended.
- Odd settings run (bulge, long frill, band, no notches, strong taper); too-narrow settings give a clear error.

## Assumed, not decided (confirm with Remy)
- Defaults: bottom and top 150 mm, middle 130 mm; frill width 60 mm; seam allowance 12 mm on every edge (including the open bottom edge, no hem); frill notch spacing 15 mm, tube notch spacing 25 mm; fabric 1470 mm; tabs 12 mm every 125 mm.
- The profile is a quadratic through the three diameters (smooth, no straight middle section).
- Frill length 0 = exactly the top circumference (pi x top diameter). A longer strip gathers, a shorter one leaves a gap (the tool warns).
- Frill notch width is worked out from the circle (each notch takes out its share of the extra allowance length), not a fixed angle. Tube notches use a fixed 50 degree V like the cone worm.
- No notches on the cap disk edge or on the top and bottom edges of the tube. Tell Claude if the cap needs them.
- The two ends of the frill strip are left to be joined by hand (no extra allowance for an end seam).
- Ring tabs: lettered A, B, ... on the tube top edge, cap and frill; side seam tabs numbered 1, 2, ...

## Not done / not verified
- Not run as the real Mac app (`install-app.sh` not run; the window and the Mac Save dialog are untested). Tool checked in a browser on a spare port.
- No test cut or sew. Laser bed size and fabric still open.
- No 3D surface for Fusion 360 (deferred, as for the whole project).

## Next
- Remy runs `./install-app.sh` here, opens Sea Anemone, tries a test cut on paper or cheap fabric.
- Settle notch depths and the frill band from the test sew.
