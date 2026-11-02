# polyps/fabric-pattern/

## Purpose
Flat nylon fabric pattern for a polyp, sewn together, with string channels. Same fabric type as inflatable costumes.

## What's here
Code, pictures and README copied unchanged from `RemyOP-LTL/Modeling`, folder `coral-polyp-pattern/`, branch `claude/project-thread-gx48mb` (pull request #1 there, not merged), on 2026-10-30. Start with `README.md` in this folder. `designs/` holds earlier options for comparison.

Re-run on 2026-10-30 to check it: `python3 make_pattern.py --out <folder>` (about 30 s; needs numpy, scipy, matplotlib, shapely) gives the same numbers as the summary and a byte-identical flat piece.

## Current design: `polyp-5-taper-tabs` (default; `polyp-5-taper-string` = continuous tunnel is `POLYP="TUNNEL=2"`; plain `polyp-5-taper` is `POLYP="TUNNEL=0"`)
- 5 fingers, each sewn from 2 mirror-image halves. Cut 10 pieces (fold the fabric, cut 5 pairs), each about 5.0 x 13.2 in.
- Round cuff, 16.21 in around (5 in tube + 0.5 in ease), 3 in tall. Finger 8.5 in long on the flat, 3.24 in wide at the crotch, tapering to a point.
- Fingers lean out 45 degrees over the first 1.5 in, then curve back to vertical.
- Seam allowance 3/8 in, hem 1 in at the cuff bottom. 5/8 in at the string tabs only (below). Cut piece is about 5.2 x 13.2 in.
- Fabric: woven, no stretch (decided 2026-10-30), so the cuff keeps 0.5 in ease.
- The 3D picture comes from a cloth simulation of the actual flat piece (air pressure, no stretch, no seam stiffness). Findings: inflated fingers come out shorter than the flat piece; they can rest spread or bunched upright; air pressure rounds off the points. It ignores gravity, fabric thickness, seam bulk, the air inlet, and fingers pressing on each other.

## String tabs (2026-11-02; replaced the continuous tunnel of 2026-10-30)
- Remy: instead of the wider seam along the whole length, a number of 1/4 to 1/2 in tabs along the inner seam, at least 3 per finger. He sews the tabs closed, which leaves less fabric where the finger should collapse easily. Default: 3 tabs of 3/8 in on the 8.5 in finger, centred 1.0, 4.5 and 8.0 in from the tip (auto: about one every 3 in, never fewer than 3). Settings `TUNNEL` (1 tabs, 2 continuous, 0 none), `TAB_LENGTH`, `TAB_COUNT`, `TAB_SPACING`, `TAB_MARGIN`, `TUNNEL_WIDTH`, `STRING_LOOP` in `make_pattern.py`.
- Tab = the two small flaps (5/8 in allowance there) lying flat and sewn together 1/4 in from the seam (blue line on the pattern), leaving a pocket for the cord.
- Cord: Dyneema, like a shoe boa lace (about 1 mm). Knot at the fingertip, stitched over. A tied loop at the centre end. Remy will make a jig so the cords come out about the same; small differences are fine.
- No stiffeners or ties. The polyp must crumple easily so the motor can stay small, so air pressure alone has to spread the fingers. Expect pattern trial and error.
- Remy's note: the simulation shows pleats and folds at the base of the fingers. They might get in the way of re-inflating, so watch them in the test sew. They also let the fingers wiggle in the wind.
- Not in the inflated simulation: the 3D picture is the same as the plain taper's. The tabs, cord and extra bulk are ignored there.
- Checked: `TUNNEL=2` and `TUNNEL=0` give piece pictures byte-identical to the earlier files.

## Tools
- `polyp_tool.py` (and the double-click `Run Polyp Tool.command`): a page that opens in the browser, with fields for cuff diameter, cuff ease, cuff length, finger length, finger count, fullness, lean out, turn length, tab length, tabs per finger, pocket width, hitch depth and fabric softness. The flat pattern redraws as you type. Buttons run the inflated and string-pull simulations. Tested in a headless browser on Linux, not yet on a Mac. Output goes to `tool-output/` (git-ignored). Cuff diameter is the input; the tube size is derived (diameter minus ease/pi).
- `sim_pull.py`: string-pull simulation. Five cords, each anchored at its fingertip, held at the tabs, run to the centre point and down to one hitch (1 in below the centre point, as Remy asked). The hitch is pulled down in 1 in steps and the fabric re-settles each time. Cord can't stretch, is just taut when inflated, no friction, constant air pressure, open tube, floppy fabric (`--soft 0.05`). Stops when the fabric would stretch over 5 % (the fingers can't fold further).
- `sim_polyp.py`: `relax()` takes an optional string, an open-tube mode and a fabric softness; the 3D drawing is a reusable `draw_polyp()`. The inflated 3D picture still uses stiff fabric (soft 1), so frame 0 of the pull picture (soft 0.05) leans out a bit more than the inflated picture.
- `snapshot.html` is the page published as the link for Remy.

## What went wrong in the first pull simulation (2026-10-31), and the fix (2026-11-02)
Remy said real fingers collapse into themselves rather than curl. The first model made the cord follow every point of the seam, which acted like a stiff spine along one side, so pressurised fingers just curled. Fix: hold the cord only at the tip, the tabs and the centre point, straight in between. I also made the fabric floppier, but tried soft 1, 0.1 and 0.02 and the shape barely changed. The guide points did the work. (Pressure alone doesn't change the shape in this model: the forces scale with it. Only the fabric stiffness compared with the pressure matters.) An early run showed huge forces because the force calculation still used the whole seam; fixed.

## String pull results (default design, 1 in hitch, tabs, soft 0.05)
- The fingers fold in on themselves and crumple toward the cuff: fingertip height 6.7 in at rest, 5.5 at 2 in of pull, 4.0 at 4 in, 2.8 at 6 in, 2.0 at 7 in, 1.2 at 8 in. The model jams between 8 and 9 in.
- Force per 1 psi of air: 0.7 lbf at 1 in, 1.8 at 2 in, 2.8 at 4 in, 5.5 at 5 in, 13.5 at 6 in, 14.2 at 7 in, 9.1 at 8 in. At 0.25 psi, a quarter of that (about 3.5 lbf at the peak). The peak is where the fingers crumple into the cuff and air has to be pushed out.
- The central string and spool need about 8 in of travel. Hand this to `../motor/`.
- Caveats: forces are per psi (scale by the real pressure); fingers pressing on each other are not simulated, so a real collapse will be less free than shown near the end; no friction at the tabs.

## Not in the design yet
- Where the air goes in, and how the cuff seals to the tube.
- The central string, the spool and the hitch hardware (see `../motor/`).

## Open questions
- Will air pressure alone spread the fingers (no stiffeners, decided)? Do the base pleats stop it re-inflating after the string is released? Only a test sew will tell.
- Fingers are 8.5 in long and lean out; neighbouring polyps on the skin may collide. Not answered yet: it needs the pentagon spacing from `skin/`, which depends on the overall size (TBD). The earlier simulations give tips about 4.7 in from the centre for 8.5 in fingers.
- Does the simulated fold-in match what Remy expects? Frame 0 looks fine, but check the shapes at 5 to 7 in against his experience.
- Do the 3 tabs hold the cord well enough, or would 4 or 5 tabs fold the fingers more evenly? Try `TAB_COUNT` in the tool.
- Will the tab pockets drag on the cord when the fingers crumple? Check in the test sew.
- Make one test finger pair to check the curve and length against the simulation.

## Next
- Make a test finger pair with tabs and a Dyneema cord, and check the curve, length and cord drag.
- Check polyp-to-polyp collision once the skin layout gives the pentagon spacing.
- **If asked:** output a 3D surface of the inflated polyp (for example STL or STEP) so Remy can design the motor and blower assembly around it in Fusion 360. Not started.
- Size the motor spool for about 8 in of central string travel and the pull force above (`../motor/`).
- Try other tab counts and finger shapes in the tool.

## Working rule (from Remy, 2026-10-30, updated 2026-10-31)
After any change to the pattern or simulation, run it and show Remy a snapshot of the outputs (the piece picture, the 3D picture, the pull picture and the PDF) in the chat. Also republish the link page `snapshot.html` (as an Artifact, with the pictures and PDF from `designs/`) and give Remy the link, so he can open anything with one click. Update the date and numbers in `snapshot.html` first.

Remy is not comfortable in the terminal. The cloud + local workflow is in the repo root `CLAUDE.md` ("Cloud + local workflow"). In short: after every change run it, show the snapshot, republish `snapshot.html`, push, and tell him which branch to pick in the simulator at http://127.0.0.1:8765/ and to press Get latest changes. Remy is also open to a local session (Claude desktop app pointed at his repo folder) if that ever becomes easier.

## Local runner (2026-11-02)
- `install-mac.sh`: one-time setup on Remy's Mac. Makes `.venv`, installs `requirements.txt`, and registers a launchd agent (`com.coral.polyptool`) that keeps `polyp_tool.py` running at http://127.0.0.1:8765/. `bash install-mac.sh --remove` undoes it. Logs: `~/Library/Logs/polyptool.log`. Tested here with launchctl, open and xcode-select replaced by stubs; not yet run on a real Mac.
- `polyp_tool.py` has a Version card: it shows the running branch and last change, lists branches on GitHub, and **Get latest changes** switches to the chosen branch, pulls, installs `requirements.txt`, and restarts itself. It refuses if a simulation is running, if local files were edited, if there are unpushed local commits, or if the branch has no simulator (`main` has none until the pull request is merged).
- The repo is public, so no GitHub login is needed to clone or pull.
- `Run Polyp Tool.command` still works as a double-click fallback (it doesn't update itself).
