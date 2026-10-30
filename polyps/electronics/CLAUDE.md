# polyps/electronics/

## Purpose
Controller, motor driver, blowers and power for the polyps.

## Design intent (from Remy)
- Air supply is its own workstream: see `../air/`.
- The motor winds the string to collapse the polyp; the blower inflates it.

## Status
Not started. Controller not chosen.

## Open questions
- Blower choice and layout (per-polyp or central), and whether airflow needs valves.
- Number of motors and blowers to drive; power budget.
- Controller (Arduino, Raspberry Pi, other).

## Next
- Settle motor choice first (`../motor/`), then size drivers and power.
