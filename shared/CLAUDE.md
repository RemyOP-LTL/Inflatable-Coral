# shared/

## Purpose
Dimensions, materials, and mounting points that all parts must agree on. Check here before assuming a number.

## Agreed so far (as of 2026-10-30)
| Item | Value | Source |
|---|---|---|
| Skin sheet | corrugated plastic, 1 mm wall, cut from 4 x 8 ft sheets | Remy |
| Plastic stretch | none assumed | Remy, 2026-10-30 |
| Test tube for skin | 12-16 in across (hex57 uses 16 in, 8 ft long, 20 ft bend radius) | Remy / hex57 |
| Polyp fabric | woven nylon, no stretch | Remy, 2026-10-30 |
| Polyp tube / cuff | cuff slides over a 5 in tube, 0.5 in ease | polyp-5-taper |
| Polyp finger | 5 fingers, 8.5 in long, 3.24 in wide at base | polyp-5-taper |
| Pentagon hole | round; size must fit the polyp tube | Remy |

## Conflicts to resolve (deferred by Remy, 2026-10-30: build general, scalable tools first; match sizes later)
- The polyp tube (5 in) needs a hole of at least about 5 in. The current hex57 layout has about 5 in pentagons with a 3.75 in hole. See `skin/CLAUDE.md`.

## File formats (2026-11-16)
`FORMATS.md` defines the saved-design files that the parts hand to the workbench: skin `layout.json` (the existing hex57 file is the contract as is) and the new polyp `polyp.json`. Decided with Remy 2026-11-16; reason in `../workbench/CLAUDE.md`.

## Next
- Skin/frame and spiral-cone sessions: follow `FORMATS.md`; tell the workbench session if a field is missing.
- Record overall size and mounting points as they are decided.
