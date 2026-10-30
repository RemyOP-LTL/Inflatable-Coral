# Coral Sculpture

## What this is
TBD (ask Remy): one or two sentences on what the sculpture is, what it looks like, and where it will be shown.

## The parts
- skin/    — Pattern for the sculpture's outer skin. A tool that turns the 3D surface into flat panels to cut. Includes a simulation of how the skin behaves.
- polyps/  — Inflatable polyps. Simulation of how they inflate, plus flat patterns to cut and seal.
- motors/  — Motor control for TBD (what moves and how).
- shared/  — Dimensions, materials, and mounting points that all parts must agree on. Check here before assuming a number.

## Key facts
Anything marked TBD has not been decided. Do not guess; ask Remy.
- Overall size: TBD (height x width)
- Skin material: TBD (the older coral used 1 mm plastic sheet, CNC-router cut, fold lines scored, 48 x 96 in sheets)
- Polyp material: TBD
- Number of polyps: TBD
- Motor controller: TBD (not chosen yet)
- CAD tool: TBD. Older work was in Onshape (FeatureScript). Fusion 360 is being considered but has not been tried.

## Reference: older work (read-only)
Repo `RemyOP-LTL/Modeling`, folder `hex-tubes/`. It is an earlier 20 ft animatronic coral skin. Look, but never edit it. Start with `HANDOFF.md` and `FUSION-CONTEXT.md`.

Lessons carried over:
- Prototype the pattern math in standalone Python first, then build it in CAD.
- Don't force panels perfectly flat; thin plastic bows a little and that is fine.
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
