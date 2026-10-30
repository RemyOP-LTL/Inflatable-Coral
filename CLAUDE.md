# Coral Sculpture

## What this is
An inflatable coral sculpture. A tube- or dome-shaped coral form is covered in a skin of flat plastic panels joined with tabs and rivets. Fabric polyps sit in the pentagon panels; they inflate with air and collapse when a motor winds a string. Where it will be shown: TBD (ask Remy).

## The parts
- skin/    — Pattern for the outer skin. A tool that turns a 3D surface into polygon panels, then into flat sections to cut. Includes a simulation of how the skin behaves.
- polyps/  — Inflatable polyps. Sub-folders:
    - fabric-pattern/ — sewn nylon pattern, string channels
    - motor/          — motor that winds the string
    - electronics/    — controller, driver, blowers
- motors/  — Reserved for any motion that is not a polyp (TBD). Polyp motors live in polyps/motor/.
- shared/  — Dimensions, materials, and mounting points that all parts must agree on. Check here before assuming a number.

## Key facts
Anything marked TBD has not been decided. Do not guess; ask Remy.
- CAD tool: **Fusion 360.** The Onshape files in the older repo are reference only.
- Overall size: TBD (height x width)
- Skin material: corrugated plastic sheet, 1 mm wall. For now only the top layer is simulated; the rest is ignored until later. Sheets are 4 x 8 ft (48 x 96 in).
- Skin test shapes: tube 12-16 in across (tubular coral), and later a domed brain-coral shape.
- Polyp material: nylon fabric, sewn, like inflatable costumes.
- Number of polyps: one per pentagon panel (count follows the skin layout).
- Polyp actuation: string wound by a motor; air from blowers. Motor: likely a stepper, not chosen.
- Motor controller: TBD (not chosen yet)

## Reference: older work (read-only)
Repo `RemyOP-LTL/Modeling`, folder `hex-tubes/`. Never edit it. The latest skin layout from there (`layouts/hex57`) has been copied into `skin/hex57/`; background notes are in `skin/reference/`.

Lessons carried over:
- Prototype the pattern math in standalone Python first, then build it in CAD.
- Don't force panels perfectly flat; the plastic bends and stretches a little.
- Neighbouring panels must share exact corner coordinates so they join into one surface.
- Make holes after joining, in bulk, not one at a time.
- Check panel size against branch thickness early. Big panels on a thin tube look like a playing card on a can.

## How we work
- One task per session. Work only in the folder the task is about, unless the task says otherwise.
- At the end of each task, update that folder's CLAUDE.md: what was done, decisions made, what's next.
- Explain things in plain language. The lead is a mechanical engineer, new to coding. Say what a script does before asking Remy to run it, and give one recommended path.
- Several people work on this repo. Don't change files outside the task's folder without saying so.

## Team
- Remy — lead
- TBD: names and who works on what
