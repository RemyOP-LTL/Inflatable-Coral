# Brief for the next shape (written 2026-11-17)

Remy prototyped the cone worm and is not happy with its shape or how it moves. The plan: keep the same approach and feature set, apply it to a NEW shape, as a separate app. This file is the starting point for that new session. Read it first, then `CLAUDE.md` in this folder for the cone worm's full history.

## Where everything is
- Repo: `RemyOP-LTL/Inflatable-Coral` on GitHub. Branch with all cone worm work: `polyp-2026-11-15-spiral-cone` (pushed; not merged into `main`, no pull request, by Remy's rule).
- Folder: `polyps/spiral-cone/`. On Remy's Mac the working clone is `~/cone-worm` (a real git clone, so the app's Refresh button can pull updates). The old plain copy `~/cone-worm-plain-copy` can be deleted.
- The installed app: `~/Applications/Cone Worm.app` (built by `install-app.sh`), runs on the first free port in 8820-8829. Other tools: skin 8790-8799, polyp tool 8800-8859. **Pick 8830-8839 for the new app and check nothing else uses it.**
- Commits (oldest first): `5abc4b4` window app + metric + sections; `8e37016` snapshots, greyed Rebuild, separate cuff switch, frill end from tip; `49fa962` DXF + forced snapshot naming; `0e8636a` Detailed / Laser cut views + PDF; `fac5ffc` black 0.001 in PDF, ask where to save; `5176b5c` seam notches + one-loop frill.

## What the cone worm app is (file map)
| File | Job |
|---|---|
| `spiral_cone.py` | The pattern maths and every output file. Settings are module variables at the top (all mm). `build()` makes the pieces; `export_items()` is the one place the exports take their lines from; `write_svg / write_pdf / write_dxf / draw_png / draw_png_outline` write files; `report()` makes the numbers text. Run alone: `python3 spiral_cone.py --out folder`. |
| `spiral_tool.py` | A small local web server (Python `http.server`) plus the whole page (HTML/JS inside one string). `FIELDS` lists every input box (section, name, label, unit, min, max, step). `/api/run` rebuilds, `/api/snapshot*` saves/loads named settings, `/api/export` asks where to save and copies the file, `/api/refresh` pulls the latest code from GitHub and restarts. |
| `cone_window.py` | The Mac window (pywebview). Starts the server as a subprocess on a free port, restarts it if it dies, stops it on close. |
| `install-app.sh` | Makes `.venv`, installs `requirements.txt`, builds the `.app` with the logo, opens it. |
| `icon/` | `cone-worm-logo.svg` (made with a small Python drawing function), `.png`, `.icns`. The new app needs its own logo. |
| `snapshots/` | Saved named settings (one JSON each; git-ignored). |

## Features to carry over to the new shape (all working, Remy likes them)
1. Mac window app, no browser; Refresh button pulls the newest branch and restarts; version label in the header.
2. Metric everywhere; fabric width is the one setting in inches (Remy buys fabric in inches).
3. Number boxes with the unit after the box, no sliders, no per-field descriptions, grouped in cards by topic (for the cone: Cone shape, Seam, Frill, Tabs).
4. Sticky tile at the top of the left column: Rebuild button (greyed when nothing changed; no "settings changed" banner), reset link, snapshot name box + Save, "Load a snapshot..." drop-down. **Remy wants this tile reproduced in his other programs too.**
5. Pattern tile with a Detailed / Laser cut switch. Warnings appear only for rebuild errors; the numbers text hides the settings block.
6. Flat pattern preview with mm and inch axes on the preview only.
7. Exports follow the view: PDF, DXF, SVG, true size in mm, no scales or grid. Names: `<snapshot>_detailed_mm.<ext>` and `<snapshot>_outline_mm.<ext>`. Asks for a snapshot name only the first time for a given set of settings; after that it reuses the name (loading or saving a snapshot also names the settings). Saving opens the Mac Save window (via `osascript`) in the last folder used; Cancel saves nothing; the page stays put with a green "Saved ..." message and Show in Finder.
8. Laser file rules learned from the cutter: PDF lines pure black, 0.001 in wide (0.072 pt), no fills, no text, no background; page = drawing + 10 mm margin, 1 pt = 1/72 in. **Every piece is ONE closed loop**; where there are slits (the frill fringe) the loop walks down each slit and back up, doubling back. No separate slit lines (the cutter rejected them).
9. Seam allowance notches that get closer together toward the tip where the curvature changes (V notches, depth, spacing at the base and at the tip as inputs).
10. Alignment tabs: numbered squares on matching edges (only on the Detailed view).

## Lessons and traps
- pywebview ignores download links unless `webview.settings["ALLOW_DOWNLOADS"] = True`, and even then the window showed a PDF preview it could not leave. Do not use browser downloads: save through the server (`/api/export`).
- pywebview's private mode makes `localStorage` unreliable: keep snapshots as files on the server side.
- Never stop processes with `pkill -f <name>`; test on a spare port and stop by its own pid. Old copy of the cone tool may be running on 8820.
- `spiral_cone.py` keeps settings in module variables, so the server sets them under a lock before each build. Keep that pattern (or pass a settings object) in the new tool.
- Verify exports by reading them back with an independent reader (`ezdxf`, `pymupdf`) in a scratch venv, not only by looking.
- The Save window and the real Mac window were checked only by starting/cancelling from the shell; Remy tested them by hand and said "worked, a bit wonky". Not yet cut on the real laser with the latest files (notches and one-loop frill are fresh).

## Not decided yet (do not guess, ask Remy)
- **What the new shape is**, how it moves, and what the "same basic approach" means for it (one strip? several pieces? a frill or other detail? tabs?). Ask first and show a quick description back before building.
- Notch numbers (depth 8 mm, spacing 60 to 20 mm) are assumptions from the prototype; fabric choice and laser bed size are still open.
- Cone worm open questions from the original brief remain open (frill strip width meaning, laser bed size, flared cuff vs separate band, fringe overlap, pitch guesses).

## Suggested way to start the new app
1. Agree the shape with Remy in plain language (5 lines), pick a short name.
2. Create a new folder `polyps/<new-name>/` and a new branch `polyp-<YYYY-MM-DD>-<new-name>` (naming rule: `<area>-<YYYY-MM-DD>-<idea>`). Do not touch `polyps/spiral-cone/`; copy files from it instead.
3. Copy `spiral_tool.py`, `cone_window.py`, `install-app.sh`, `requirements.txt`, `.gitignore` and change names, ports (8830-8839), window title, logo. Write a new `<shape>.py` with the same outputs and the same `export_items()` idea; replace the `FIELDS` list.
4. Run it on a spare port, check every export by reading it back, then build the Mac app.
5. Standing rules: commit only when told; never merge or open a pull request without Remy's yes (remind him at the end); update the folder's `CLAUDE.md`; explain scripts in plain language before running them.
