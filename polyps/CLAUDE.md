# polyps/

## Purpose
Inflatable polyps. One sits in each pentagon panel of the skin.

## Sub-folders
- `air/` — blowers, ducting and pressure (a separate workstream).
- `fabric-pattern/` — the sewn nylon pattern, including string channels.
- `motor/` — the motor that winds the string.
- `electronics/` — custom board with motor controllers and LEDs; controller, power.

## How a polyp works (from Remy)
- Made of nylon fabric, sewn together, like inflatable costumes.
- Air (back pressure) inflates it. Either one small blower per polyp, or one large central blower; depends on polyp size and design.
- **String (decided 2026-10-30): five-finger pull.** The seam running along each finger becomes a tunnel for that finger's string. The string is sewn in at the very tip, runs freely inside the tunnel, and ends in a loop where all five meet. One central string hitches through the five loops and winds onto a spool on the motor. The spool must be big enough to take the bunched-up strings as they wind in.
- A motor winds up the string to collapse the polyp. Releasing the string lets the air inflate it again.

## Status
Fabric pattern in `fabric-pattern/` (copied from the Modeling repo and re-run successfully). Design `polyp-5-taper`: 5 fingers on a cuff that slides over a 5 in tube. Motor and electronics not started.

## Open questions
- Polyp size and finger count (sets pentagon size in `skin/`).
- Air: see `air/`.
- Tunnel detail: can the existing 3/8 in seam allowance form the tunnel, or does it need extra fabric? String material and tip anchor.

## Next
- Settle polyp size against the skin hole (see `shared/CLAUDE.md`).
- Add the string tunnels to the pattern (`fabric-pattern/`).
- Size the motor spool and pull force (`motor/`).
