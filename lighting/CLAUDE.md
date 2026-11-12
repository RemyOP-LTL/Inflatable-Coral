# lighting/

## Purpose
Integrated illumination for the whole sculpture: how the coral is lit, what is lit, and how the lighting is controlled and powered.

## Design intent (from Remy)
- The coral has integrated illumination (2026-10-30). Details not yet given; Remy wants to keep things general for now.
- The LEDs that sit with each polyp are planned to go on the custom board in `../polyps/electronics/`. This folder covers the sculpture-wide view.

## Status
Not started.

## Open questions
- What is lit: polyps only, skin panels too (the cutouts in the plastic could glow), or both?
- Light type: addressable LED strips or pixels, discrete LEDs on the polyp board, other?
- Control: shared with the motion control, so lights can follow the waves and react to people?
- Power budget and wiring for a 20 ft off-grid piece; how it reads in daylight and at night.
- Where the line sits between this folder and the polyp board (suggestion: per-polyp LEDs on the board; overall design, effects and power distribution here).

## Next
- Remy to describe the look he wants (colours, where light shows, behaviour with the motion).
