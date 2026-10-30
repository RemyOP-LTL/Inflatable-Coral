# Coral Sculpture

## What this is
An inflatable coral sculpture. A tube- or dome-shaped coral form is covered in a skin of flat plastic panels joined with tabs and rivets. Fabric polyps sit in the pentagon panels; they inflate with air and collapse when a motor winds a string. Where it will be shown: TBD (ask Remy).

## The parts
- skin/    — Pattern for the outer skin. A tool that turns a 3D surface into polygon panels, then into flat sections to cut. Includes a simulation of how the skin behaves.
- polyps/  — Inflatable polyps. Sub-folders:
    - fabric-pattern/ — sewn nylon pattern, string channels
    - motor/          — motor that winds the string
    - electronics/    — controller, driver, power
    - air/            — blowers, ducting, pressure (workstream, just started)
- shared/  — Dimensions, materials, and mounting points that all parts must agree on. Check here before assuming a number.

## Key facts
Anything marked TBD has not been decided. Do not guess; ask Remy.
- CAD tool: **Fusion 360.** The Onshape files in the older repo are reference only.
- Overall size: TBD (height x width)
- Skin material: corrugated plastic sheet, 1 mm wall. For now only the top layer is simulated; the rest is ignored until later. Sheets are 4 x 8 ft (48 x 96 in).
- Skin holes: pentagons get normal (round) holes for the polyps; all other polygons get the offset cutout that thins toward the middle of each shared edge.
- Skin test shapes: tube 12-16 in across (tubular coral), and later a domed brain-coral shape.
- Polyp material: nylon fabric (woven, no stretch), sewn, like inflatable costumes. Default design `polyp-5-taper`: 5 fingers, cuff slides over a 5 in tube. See `polyps/fabric-pattern/`.
- Number of polyps: one per pentagon panel (count follows the skin layout).
- Polyp actuation: five finger strings, one per finger, run in a tunnel on each finger's seam and meet at a loop; a central string hitched through the five loops winds onto a motor spool. Air from blowers (see polyps/air/). Motor: likely a stepper, not chosen.
- Design goal for now: build generalized, scalable tools. Matching skin hole size to polyp size is deferred until things can be scaled and changed easily.
- Motor controller: TBD (not chosen yet)
- Fusion 360 integration (how the skin layout gets into Fusion): decided to deal with it later.

## Reference: older work (read-only)
Repo `RemyOP-LTL/Modeling`, folder `hex-tubes/`. Never edit it. The latest skin layout from there (`layouts/hex57`) has been copied into `skin/hex57/`; background notes are in `skin/reference/`.

Lessons carried over:
- Prototype the pattern math in standalone Python first, then build it in CAD.
- Don't force panels perfectly flat. The plastic bends but is treated as not stretching (decided 2026-10-30), so shared edge lengths must match.
- Neighbouring panels must share exact corner coordinates so they join into one surface.
- Make holes after joining, in bulk, not one at a time.
- Check panel size against branch thickness early. Big panels on a thin tube look like a playing card on a can.

## How we work
- **Merging:** work happens on a branch, and Remy forgets to merge. At the end of every session, and whenever a piece of work is finished, remind Remy and ask whether to open a pull request and merge the branch into main. Do not merge without a yes.
- One task per session. Work only in the folder the task is about, unless the task says otherwise.
- At the end of each task, update that folder's CLAUDE.md: what was done, decisions made, what's next.
- Explain things in plain language. The lead is a mechanical engineer, new to coding. Say what a script does before asking Remy to run it, and give one recommended path.
- Several people work on this repo. Don't change files outside the task's folder without saying so.

## Team
- Remy — lead
- TBD: names and who works on what
