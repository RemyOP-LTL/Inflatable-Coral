# polyps/

## Purpose
Inflatable polyps. One sits in each pentagon panel of the skin.

## Sub-folders
- `air/` — blowers, ducting and pressure (a separate workstream).
- `fabric-pattern/` — the sewn nylon pattern, including string channels (5-finger design).
- `spiral-cone/` — a second design, started 2026-11-15: one long strip wound in a spiral into a cone, with a spiral ruffle, a cuff, and one string down the axis. Fewer pieces and seams than the 5-finger design. Pattern tool on port 8820. Kept as its own tool, not merged into the polyp tool (Remy, 2026-11-16). See its `HANDOFF.md` and `CLAUDE.md`.
- `motor/` — the motor that winds the string.
- `electronics/` — custom board with motor controllers and LEDs; controller, power.

## How a polyp works (from Remy)
- Made of nylon fabric, sewn together, like inflatable costumes.
- Air (back pressure) inflates it. Either one small blower per polyp, or one large central blower; depends on polyp size and design.
- **String (decided 2026-10-30): five-finger pull.** The seam running along each finger becomes a tunnel for that finger's string. The string is sewn in at the very tip, runs freely inside the tunnel, and ends in a loop where all five meet. One central string hitches through the five loops and winds onto a spool on the motor. The spool must be big enough to take the bunched-up strings as they wind in.
- A motor winds up the string to collapse the polyp. Releasing the string lets the air inflate it again.

## Status
Two designs. The 5-finger one did not work as hoped in a prototype and takes too much sewing. The spiral cone (`spiral-cone/`) is the new direction; first flat-pattern generator done 2026-11-15, nothing sewn yet.

5-finger design:
Fabric pattern in `fabric-pattern/` (copied from the Modeling repo and re-run successfully). Design `polyp-5-taper`: 5 fingers on a cuff that slides over a 5 in tube. Motor and electronics not started.

## Open questions
- Polyp size and finger count (sets pentagon size in `skin/`).
- Air: see `air/`.
- Tunnel detail: can the existing 3/8 in seam allowance form the tunnel, or does it need extra fabric? String material and tip anchor.

## Next
- Settle polyp size against the skin hole (see `shared/CLAUDE.md`).
- Add the string tunnels to the pattern (`fabric-pattern/`).
- Size the motor spool and pull force (`motor/`).
