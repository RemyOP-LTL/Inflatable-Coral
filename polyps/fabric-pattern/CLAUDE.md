# polyps/fabric-pattern/

## Purpose
Flat nylon fabric pattern for a polyp, sewn together, with string channels. Same fabric type as inflatable costumes.

## What's here
Code, pictures and README copied unchanged from `RemyOP-LTL/Modeling`, folder `coral-polyp-pattern/`, branch `claude/project-thread-gx48mb` (pull request #1 there, not merged), on 2026-10-30. Start with `README.md` in this folder. `designs/` holds earlier options for comparison.

Re-run on 2026-10-30 to check it: `python3 make_pattern.py --out <folder>` (about 30 s; needs numpy, scipy, matplotlib, shapely) gives the same numbers as the summary and a byte-identical flat piece.

## Current design: `polyp-5-taper` (default)
- 5 fingers, each sewn from 2 mirror-image halves. Cut 10 pieces (fold the fabric, cut 5 pairs), each about 5.0 x 13.2 in.
- Round cuff, 16.21 in around (5 in tube + 0.5 in ease), 3 in tall. Finger 8.5 in long on the flat, 3.24 in wide at the crotch, tapering to a point.
- Fingers lean out 45 degrees over the first 1.5 in, then curve back to vertical.
- Seam allowance 3/8 in, hem 1 in at the cuff bottom.
- Fabric: woven, no stretch (decided 2026-10-30), so the cuff keeps 0.5 in ease.
- The 3D picture comes from a cloth simulation of the actual flat piece (air pressure, no stretch, no seam stiffness). Findings: inflated fingers come out shorter than the flat piece; they can rest spread or bunched upright; air pressure rounds off the points. It ignores gravity, fabric thickness, seam bulk, the air inlet, and fingers pressing on each other.

## Not in the design yet
- The pull string and its channels (centre pull, or a channel inside each finger). Needed for the motor.
- Where the air goes in, and how the cuff seals to the tube.

## Open questions
- Do the fingers need ties or stiffeners to stay spread, or is a shake while inflating enough? Only a test sew will tell.
- Fingers are 8.5 in long and lean out; neighbouring polyps on the skin may collide. Check against the skin layout.
- Make one test finger pair to check the curve and length against the simulation.

## Next
- Add the string channels to the pattern once Remy picks centre pull or per-finger pull.
