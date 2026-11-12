# Letter-size paper prototype (2026-11-07)

A one-off iteration of `polyp-5-taper-tabs`, shrunk so the whole flat piece prints on **one 8.5 x 11 in sheet** (landscape). For quick paper prototyping on Remy's printer. It is not the default design, and the main designs in `../../designs/` are unchanged.

## Sizes (64 % of full size, scale 0.6348)

| | Full size | This prototype |
|---|---|---|
| **Cuff diameter (finished)** | 5.16 in | **3.275 in (about 3 1/4 in)** |
| Cuff goes round | 16.21 in | 10.29 in |
| Tube it slides over | 5.00 in | 3.17 in (about 3 3/16 in) |
| Cuff ease | 0.50 in | 0.32 in |
| Cuff height | 3.00 in | 1.90 in |
| Finger length (flat) | 8.50 in | 5.40 in |
| Piece width at the crotch | 3.24 in | 2.06 in |
| Seam allowance | 0.375 in | 0.238 in |
| Hem | 1.00 in | 0.63 in |
| Cut piece | 5.15 x 13.23 in | 3.27 x 8.40 in |
| String tabs | 3, each 0.375 in | 3, each 0.238 in, centred 0.63, 2.86 and 5.09 in from the tip |

Fingers (5), the 45 degree lean, the shapes and all angles are the same as the full-size design.

## Files
- `polyp-5-taper-tabs-letter-pattern.pdf`: the pattern. **Print at 100 % / Actual size, landscape**, and check the 1 in test square measures 1 in. One page.
- `polyp-5-taper-tabs-letter-piece.png`: quick picture of the flat piece.
- `polyp-5-taper-tabs-letter-piece.dxf` and `...-letter-sheet.dxf` (with `...-letter-sheet.png`): laser-cutter files at this size, cut lines only (one layer, `CUT`). The sheet has all 10 pieces nested, 19.7 x 13.4 in (501 x 342 mm). The DXF units are millimetres: the piece is 83.1 x 213.4 mm.
- `polyp-5-taper-tabs-letter-3d.png`: simulated inflated polyp at this size.
- `polyp-5-taper-tabs-letter-pull.png` and `.csv`: string-pull simulation at this size. Forces are lbf per 1 psi and are for this small model.

## How to make the paper prototype
- Cut 10 pieces (5 mirrored pairs). Print the page 5 times, then flip the paper over and print it 5 more times mirrored, or fold the paper in two and cut 5 pairs, or cut the same piece 10 times and flip 5 of them over.
- Sew or tape on the dashed line. The solid line is the cut line. Seams, notches, the slash to the dot and the string tabs work as in `../../README.md` ("How to sew it" and "The string tabs").
- Paper won't inflate, so this checks the cuff size, finger shape, seams and tab positions.

## How it was made
From commit `d33919b` on branch `claude/polyp-string-fingers`:

    POLYP="FIT_LETTER=1" python3 make_pattern.py --out iterations/letter-prototype-2026-11-07
    POLYP="FIT_LETTER=1" python3 sim_pull.py --out iterations/letter-prototype-2026-11-07
