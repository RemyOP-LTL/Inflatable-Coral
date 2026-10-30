# polyps/fabric-pattern/

## Purpose
Flat nylon fabric pattern for a polyp, sewn together, with string channels. Same fabric type as inflatable costumes.

## What's here
Code, pictures and README copied unchanged from `RemyOP-LTL/Modeling`, folder `coral-polyp-pattern/`, branch `claude/project-thread-gx48mb` (pull request #1 there, not merged), on 2026-10-30. Start with `README.md` in this folder. `designs/` holds earlier options for comparison.

Re-run on 2026-10-30 to check it: `python3 make_pattern.py --out <folder>` (about 30 s; needs numpy, scipy, matplotlib, shapely) gives the same numbers as the summary and a byte-identical flat piece.

## Current design: `polyp-5-taper-string` (default; `polyp-5-taper` without the tunnel is `POLYP="TUNNEL=0"`)
- 5 fingers, each sewn from 2 mirror-image halves. Cut 10 pieces (fold the fabric, cut 5 pairs), each about 5.0 x 13.2 in.
- Round cuff, 16.21 in around (5 in tube + 0.5 in ease), 3 in tall. Finger 8.5 in long on the flat, 3.24 in wide at the crotch, tapering to a point.
- Fingers lean out 45 degrees over the first 1.5 in, then curve back to vertical.
- Seam allowance 3/8 in, hem 1 in at the cuff bottom. 5/8 in on the string seam only (below). Cut piece is now about 5.3 x 13.2 in.
- Fabric: woven, no stretch (decided 2026-10-30), so the cuff keeps 0.5 in ease.
- The 3D picture comes from a cloth simulation of the actual flat piece (air pressure, no stretch, no seam stiffness). Findings: inflated fingers come out shorter than the flat piece; they can rest spread or bunched upright; air pressure rounds off the points. It ignores gravity, fabric thickness, seam bulk, the air inlet, and fingers pressing on each other.

## String tunnel (added 2026-10-30)
- Seam allowance made wider (5/8 in) on the string seam only: the finger's inner edge from the tip, then the triangle's straight edge to the centre point. 11.25 in on the flat piece. Remy's call, not extra strips and not a bought tape.
- Tunnel = the two allowances left sticking out, sewn together 1/4 in from the seam (blue line on the pattern). The cord runs between them. Settings `TUNNEL`, `TUNNEL_WIDTH`, `STRING_LOOP` in `make_pattern.py`.
- Cord: Dyneema, like a shoe boa lace (about 1 mm). Knot at the fingertip, stitched over. A tied loop at the centre end. Remy will make a jig so the cords come out about the same; small differences are fine.
- No stiffeners or ties. The polyp must crumple easily so the motor can stay small, so air pressure alone has to spread the fingers. Expect pattern trial and error.
- Remy's note: the simulation shows pleats and folds at the base of the fingers. They might get in the way of re-inflating, so watch them in the test sew. They also let the fingers wiggle in the wind.
- Not in the simulation: the 3D picture is the same as the plain taper's. The tunnel, cord and extra bulk are ignored.
- Checked: `POLYP="TUNNEL=0"` gives a piece picture byte-identical to the old `polyp-5-taper-piece.png`. The 3D picture of the new default is identical to the old one.

## Not in the design yet
- Where the air goes in, and how the cuff seals to the tube.
- The central string, the spool and the hitch (see `../motor/`).

## Open questions
- Will air pressure alone spread the fingers (no stiffeners, decided)? Do the base pleats stop it re-inflating after the string is released? Only a test sew will tell.
- Fingers are 8.5 in long and lean out; neighbouring polyps on the skin may collide. Not answered yet: it needs the pentagon spacing from `skin/`, which depends on the overall size (TBD). The earlier simulations give tips about 4.7 in from the centre for 8.5 in fingers.
- Will the 1/4 in tunnel drag on the cord when the fingers crumple? Check in the test sew.
- Make one test finger pair to check the curve and length against the simulation.

## Next
- Make a test finger pair with the tunnel and a Dyneema cord, and check the curve, length and cord drag.
- Check polyp-to-polyp collision once the skin layout gives the pentagon spacing.
- **If asked:** output a 3D surface of the inflated polyp (for example STL or STEP) so Remy can design the motor and blower assembly around it in Fusion 360. Not started.
- Size the motor spool for five bunched cords plus the central string (`../motor/`).

## Working rule (from Remy, 2026-10-30)
After any change to the pattern or simulation, run it and send Remy a snapshot of the outputs (the piece picture, the 3D picture and the PDF) in the chat, so he can see the effect without going to GitHub.
