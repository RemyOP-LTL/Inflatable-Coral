# Coral Sculpture

## What this is
A large coral sculpture, 20 ft tall, with living polyps and integrated illumination, for Burning Man. A tube- or dome-shaped coral form is covered in a skin of flat plastic panels joined with tabs and rivets. Fabric polyps sit in the pentagon panels; they inflate with air and collapse when a motor winds a string. Remy wants to keep the description general for now; details of the look and the motion are still to be settled.

**Deadline:** finished by **August 15, 2027**, to leave time to transport it to Burning Man. Today is 2026-10-30, so about nine and a half months.

## The parts
- skin/    — Pattern for the outer skin. A tool that turns a 3D surface into polygon panels, then into flat sections to cut. Includes a simulation of how the skin behaves.
- polyps/  — Inflatable polyps. Sub-folders:
    - fabric-pattern/ — sewn nylon pattern, string channels
    - motor/          — motor that winds the string
    - electronics/    — custom board with motor controllers and LEDs; controller, power
    - air/            — blowers, ducting, pressure (workstream, just started)
- lighting/ — Integrated illumination for the whole sculpture (not started)
- shared/  — Dimensions, materials, and mounting points that all parts must agree on. Check here before assuming a number.

## Key facts
Anything marked TBD has not been decided. Do not guess; ask Remy.
- CAD tool: **Fusion 360.** The Onshape files in the older repo are reference only.
- Overall size: **20 ft tall** (assumed, per Remy 2026-10-30); width TBD. The 12-16 in tube is a test shape; whether it is a real branch size is not settled.
- Illumination: integrated lighting is part of the sculpture. Not designed yet; see `lighting/`. Per-polyp LEDs are planned for the custom board in `polyps/electronics/`.
- Venue: Burning Man (outdoor desert: wind, dust, off-grid power, transport and assembly on site). Not yet worked through; raise when relevant.
- Skin material: corrugated plastic sheet, 1 mm wall. For now only the top layer is simulated; the rest is ignored until later. Sheets are 4 x 8 ft (48 x 96 in).
- Skin holes: pentagons get normal (round) holes for the polyps; all other polygons get the offset cutout that thins toward the middle of each shared edge.
- Cutting: Remy plans to buy his own CNC router and cut the plastic himself. Likely choice: a 4 x 8 ft Avid CNC router (not bought yet), which fits the 4 x 8 ft sheets. Exact model, tooling and usable cutting area still to confirm, since they limit part size and cut details. Fusion 360 CAM is for this.
- Skin test shapes: tube 12-16 in across (tubular coral), and later a domed brain-coral shape.
- Polyp material: nylon fabric (woven, no stretch), sewn, like inflatable costumes. Default design `polyp-5-taper`: 5 fingers, cuff slides over a 5 in tube. See `polyps/fabric-pattern/`.
- Number of polyps: one per pentagon panel (count follows the skin layout).
- Polyp actuation: five finger strings, one per finger, run in a tunnel on each finger's seam and meet at a loop; a central string hitched through the five loops winds onto a motor spool. Air from blowers (see polyps/air/). Motor: likely a stepper, not chosen.
- Design goal for now: build generalized, scalable tools. Matching skin hole size to polyp size is deferred until things can be scaled and changed easily.
- Motor controller: TBD (not chosen yet)
- Motion (Remy's assumption, 2026-10-30; details later): waves of motion across the polyps, all-at-once inflation, and ideally some reactivity to people. This means each polyp (or group) must be individually controllable, and some sensing is likely needed. Not designed yet.

## Goals and workflow
Remy wants **generalized, scalable tools**, not a one-off model: change a parameter (tube size, polygon size, polyp size) and the skin and polyps update. Matching sizes between parts comes later, once things scale easily.

Who does what:
- **Claude** does the complicated surfacing: laying the polygon pattern on a surface, flattening it into cuttable sections, and the polyp pattern and simulation math. Python first, as standalone scripts.
- **Remy** is very proficient in CAD. He will model things in Fusion 360 from time to time to point Claude in the right direction. What Remy does by hand versus hands to Claude is not settled yet; ask when a task could go either way.

What each part must hand to Remy:
- **Skin:** the layout is generated in Python. It goes into Fusion 360 so Remy can tweak and adjust it and look at the CAM (cutting) side. It must arrive as editable geometry, with shared corners and flat sections ready for a 4 x 8 ft sheet. How it gets into Fusion is deferred.
- **Polyp fabric pattern:** besides the flat sewing pattern, output a **3D surface** of the inflated polyp. Remy designs the motor and blower assembly around that surface himself.

Sessions: this repo's top-level planning (this file, goals, structure) is kept in one planning session. Detailed work happens in separate sessions, one per folder or topic (for example, the polyp string and fingers).

## Reference: older work (read-only)
Repo `RemyOP-LTL/Modeling`, folder `hex-tubes/`. Never edit it. The latest skin layout from there (`layouts/hex57`) has been copied into `skin/hex57/`; background notes are in `skin/reference/`.

Lessons carried over:
- Prototype the pattern math in standalone Python first, then build it in CAD.
- Don't force panels perfectly flat. The plastic bends but is treated as not stretching (decided 2026-10-30), so shared edge lengths must match.
- Neighbouring panels must share exact corner coordinates so they join into one surface.
- Make holes after joining, in bulk, not one at a time.
- Check panel size against branch thickness early. Big panels on a thin tube look like a playing card on a can.

## How we work
- **Branch names (Remy asked for this, 2026-11-12):** `<area>-<YYYY-MM-DD>-<idea>`, lowercase with hyphens. Area is one of `skin`, `polyp`, `air`, `lighting`, `electronics`, `motor`, `shared`, `planning`, `setup`. Example: `skin-2026-11-12-geodesic-frame`. A milestone worth coming back to gets a tag with the same name plus `-v1`, `-v2`. Use the same name for the output folder of that attempt, so code and results can be found together. Name every branch you create this way. If the app assigns a name (for example `claude/...`), say in your first message what the branch is for, and keep the status page up to date so he can match them.
- **Merging:** work happens on a branch, and Remy forgets to merge. At the end of every session, and whenever a piece of work is finished, remind Remy and ask whether to open a pull request and merge the branch into main. Do not merge without a yes.
- One task per session. Work only in the folder the task is about, unless the task says otherwise.
- At the end of each task, update that folder's CLAUDE.md: what was done, decisions made, what's next.
- Explain things in plain language. The lead is a mechanical engineer, new to coding. Say what a script does before asking Remy to run it, and give one recommended path.
- Several people work on this repo. Don't change files outside the task's folder without saying so.

## Cloud + local workflow (agreed with Remy, 2026-11-02)
Remy works in the cloud with Claude and tests locally on his Mac. Keep it this way in every session:
- **Claude works in the cloud and pushes to a branch.** Remy runs the simulators on his own Mac, from a copy of this repo in `~/coral-simulator`. It is set up once with `polyps/fabric-pattern/install-mac.sh`, and the simulator then runs all the time at **http://127.0.0.1:8800/** (bookmarked). The page has a branch box and a **Get latest changes** button that pulls whatever Claude pushed and restarts it. No terminal needed after setup.
- **After every change**, in this order: run it and check it; show Remy a snapshot of the outputs in chat; update and republish the link page (`snapshot.html` in the part's folder, as an Artifact) and give him the link; commit and push; then tell him in one line: "Pushed to branch `<name>`. In the simulator, pick that branch and press Get latest changes." Say which branch every time, because each cloud session usually makes a new one.
- **Remy never types commands**, except the one-time setup paste (the batch is in `polyps/fabric-pattern/README.md`, section "Run it on your Mac"). If a later change needs more setup, give him a new paste-able batch (small, one block at a time) and say what it does first. New Python libraries go in `requirements.txt`. The update button installs them on its own.
- **Every part that gets a simulator or tool** (skin, polyps) should follow the same pattern: a script that opens a page on `127.0.0.1`, listed in this workflow, updatable from the same button. Don't invent a second way to run things.
- **Ports (each tool has its own, so they never clash):** skin tool `skin/hex57/skin_app.py` uses 8765 (and moves up to 8784 if busy); polyp tool `polyps/fabric-pattern/polyp_tool.py` uses **8800**. A new tool takes the next block (8820, 8840, ...) and gets added here. Never reuse a port, and tell Remy the exact link for each tool.
- **Keep the local copy updatable.** Never rely on Remy editing files locally. The update button refuses to overwrite local edits or unpushed commits.
- After a pull request is merged to main, the branch box on his Mac can switch to `main`. The simulator must be on main before that works.
- Remind Remy at the end of each session about merging (see "How we work").

## Team
- Remy — lead
- No one else yet. Remy will update this section when that changes.
