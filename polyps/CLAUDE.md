# polyps/

## Purpose
Inflatable polyps. One sits in each pentagon panel of the skin.

## Sub-folders
- `fabric-pattern/` — the sewn nylon pattern, including string channels.
- `motor/` — the motor that winds the string.
- `electronics/` — controller, motor driver, blowers, power.

## How a polyp works (from Remy)
- Made of nylon fabric, sewn together, like inflatable costumes.
- Air (back pressure) inflates it. Either one small blower per polyp, or one large central blower; depends on polyp size and design.
- A string is built in. Either it pulls from the centre of the polyp, or it pulls on each finger, running through a channel on the inside (toward the centre) of each finger, all tied together at the centre.
- A motor winds up the string to collapse the polyp. Releasing the string lets the air inflate it again.

## Status
Fabric pattern in `fabric-pattern/` (copied from the Modeling repo and re-run successfully). Design `polyp-5-taper`: 5 fingers on a cuff that slides over a 5 in tube. Motor and electronics not started.

## Open questions
- Polyp size and finger count (sets pentagon size in `skin/`).
- Per-polyp blowers or central blower.
- Centre pull or per-finger pull.

## Next
- Settle polyp size against the skin hole (see `shared/CLAUDE.md`).
- Choose centre pull or per-finger pull, then add string channels to the pattern.
