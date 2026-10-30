# polyps/electronics/

## Purpose
Design a custom circuit board for the polyps, carrying motor controllers and LEDs. Also covers the controller, power and wiring that go with it.

## Design intent (from Remy)
- A custom board with motor controllers and LEDs on it (decided 2026-10-30).
- Air supply is its own workstream: see `../air/`.
- The motor winds the string to collapse the polyp; the blower inflates it.
- Motion should allow waves across polyps, all-at-once inflation, and some reactivity to people, so each polyp (or small group) needs to be individually controllable (see root `CLAUDE.md`).
- Sculpture-wide lighting design lives in `../../lighting/`.

## Status
Not started. No board design, controller or motor chosen.

## Open questions
- One board per polyp, or one board driving several polyps?
- Motor and driver type (stepper is likely; see `../motor/`), which sets the driver chip and current.
- LEDs: type and count per polyp, and whether they are driven from this board.
- Controller: on the board (a microcontroller) or a central one talking to many boards; communication between boards.
- Does the board also switch the blower? Sensors for reacting to people: where do they connect?
- Power: voltage, total current for a 20 ft piece, off-grid at Burning Man.
- Which board tool (for example KiCad or Fusion Electronics) and who fabricates the boards.

## Next
- Settle the motor choice first (`../motor/`), then list the board's inputs and outputs per polyp.
