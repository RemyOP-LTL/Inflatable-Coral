# polyps/electronics/

## Purpose
Controller, motor driver, blowers and power for the polyps.

## Design intent (from Remy)
- Air comes from individual blowers or one large central blower, depending on polyp size and design.
- The motor winds the string to collapse the polyp; the blower inflates it.

## Status
Not started. Controller not chosen.

## Open questions
- Blower choice and layout (per-polyp or central), and whether airflow needs valves.
- Number of motors and blowers to drive; power budget.
- Controller (Arduino, Raspberry Pi, other).

## Next
- Settle motor choice first (`../motor/`), then size drivers and power.
