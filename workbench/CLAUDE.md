# workbench/

## Purpose
One page with tabs (Skin, Polyp, Combined) that shows any saved design version from any branch or tag. It replaces opening a different preview page per session. It only **views**; the generators (skin tool, polyp tool, frame tool, spiral tool) stay where they are.

## Why it exists (diagnosis, 2026-11-16)
Remy saw the branch button refuse or switch things. Causes found in the code:
1. Each tool ships **inside the branch it shows**. `Get latest changes` does `git checkout` of the chosen branch in the one local copy (`~/coral-simulator`), so choosing a branch also swaps the tool itself and its files.
2. A tool refuses a branch that lacks its own script (`polyp_tool.py` refuses a branch with no polyp tool, `spiral_tool.py` refuses `main`).
3. Port clash: `skin-2026-11-12-geodesic-frame` (`frame_app.py`) and `polyp-2026-11-15-spiral-cone` (`spiral_tool.py`) both chose **8820**, the same "next free block" from the root CLAUDE.md. Whichever starts second can't open its page, or shows the other tool.
4. One local copy can only be on one branch at a time, so two sessions on two branches collide.

## How it fixes this
- **Viewer** (this folder) lives on its own copy of the repo, `~/coral-workbench`, which stays on one branch and is never switched by the simulators.
- **Designs** are plain files (`layout.json`, `polyp.json`) in each experiment's folder; format in `shared/FORMATS.md`.
- The viewer reads them with `git show <branch>:<path>`: it can look at any branch or tag without checking it out.
- Version picker = a dropdown of all branches (newest first) and tags, then a dropdown of designs found in that version.
- Combined tab = the skin loaded in the Skin tab plus the polyp loaded in the Polyp tab; one polyp at every pentagon centre, turned to its normal, with flags for hole mismatch and finger overlap.

## What's here
- `workbench.py` live server, port **8840** (block 8840-8859), standard library only.
- `viewer.html` the page (three.js 0.128.0 from cdn.jsdelivr.net, like the older viewers). It runs from two sources: live (this server) or baked (data inside the page).
- `build_snapshot.py` bakes chosen versions into one page, for publishing as an Artifact so it works anywhere (phone). Artifacts can't fetch files, so baked pages show only what was picked when built.
- `install-mac.sh` one-time Mac setup (own clone in `~/coral-workbench`, starts at login). `Start Workbench.command` = double-click fallback.
- Outside this folder (said to Remy): `polyps/fabric-pattern/export_bundle.py` (new file; writes the polyp bundle, existing code untouched), `polyps/fabric-pattern/bundles/polyp-5-taper-tabs/polyp.json`, `shared/FORMATS.md`, root `CLAUDE.md` (area, parts list, port).

## Decisions (Remy, 2026-11-16)
- Failure was the branch button refusing/switching things.
- Both a local live page and a baked Artifact page, same viewer code.
- Pick by dropdown of branches and tags.
- Remy asked for running generators from the page too. Recommendation was viewer-only first; done in stages: **stage 1 (this session) = viewer**. Stage 2 is open (see Next).
- Port 8840, not 8820 (8820 was already taken twice).

## Known limits
- Tested in headless Chromium here, with three.js served locally (the CDN is blocked in this sandbox). Not yet run on Remy's Mac.
- Skin panels are drawn as flat fans: thick/curved geodesic parts (hubs, spokes) show as their outline only.
- Baked page: shows only the versions picked at build time; no GitHub refresh.
- The polyp mesh is the single-finger simulation copied round five times; fingers pressing on each other are not simulated.

## Next
- Remy to run `install-mac.sh` and try it; report what breaks.
- Stage 2: launching generators from the page. Option A (recommended): the page's Run button starts each branch's own tool in a throw-away folder (`git worktree`) on its own port, so branches never collide. Option B: leave the generators alone, and only add a "how to make this bundle" line per design.
- Spiral-cone and geodesic sessions: write a `polyp.json` / keep `layout.json` per `shared/FORMATS.md`, and move any tool off port 8820 (use 8860 and up).
- After merge to main: re-run `bash install-mac.sh main` so the workbench follows main.
