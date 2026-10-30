# polyps/air/

## Purpose
How the polyps get inflated: blowers, ducting, pressure. A separate workstream from the fabric pattern.

## Remy's thinking (2026-10-30)
- Depends on polyp size. Leaning toward **larger polyps with an individual blower each**.
- Concern: blowers with long ducting lose some of their ability to make the pressure needed to inflate things.
- **Smaller polyps with one central blower** would work best on tubular structures: sew an inner fabric skin (an internal bladder) inside the plastic skin, with holes in it, and seal each polyp to a hole. All the polyps then act as one huge balloon.
- Consequence for the motor: with a shared bladder the motor must pull against full pressure. With individual blowers, pressure can be turned down as the string pulls in.

## Status
Not started. No blower chosen.

## Open questions
- Pressure and airflow needed to inflate one polyp (needs the polyp volume from the pattern; the simulation in `../fabric-pattern/` can give a first estimate).
- Where the individual blower sits, and how its noise and size fit behind the skin.
- Central bladder: material, leakage at the polyp seals, and whether it works on a dome shape.

## Next
- Estimate the volume of a `polyp-5-taper` and the pressure needed to hold its shape.
