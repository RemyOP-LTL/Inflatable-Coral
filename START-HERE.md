# Start here (Remy's routine)

Claude: **say this to Remy at the start of every session**, in these words or shorter.

## Every session
1. Open the **Coral Frame Tool** app (Dock icon, or Finder > your home folder > Applications). It opens its own window. No browser, no terminal.
2. When Claude says it changed something, press **Refresh tool** (top right of that window). The window reloads itself with the newest version.

That is all. Leave the window open next to the Claude conversation.

## Only once (already done on this Mac, 2026-11-16)
- In Terminal, in `skin/skin-2026-11-12-geodesic-frame/`, run `./install-app.sh`. It installs the libraries and makes the app. Run it again only if the repo folder is moved. First time you open the app macOS may say it is from an unidentified developer: right-click the app, Open, Open.
- To keep it in the Dock: right-click its Dock icon, Options, Keep in Dock.

## What Refresh does
Pulls newer changes from GitHub if there are any and it is safe, then restarts the tool from the files in the repo folder (so changes Claude makes locally show up too), then reloads the window. If a change needs a new library, Refresh installs it.

## If something goes wrong
- The log is `~/Library/Logs/coral-frame-tool.log`. Tell Claude what happened.
- Window won't open: re-run `./install-app.sh`.

## For Claude (keep this true)
- Remy works locally. After you change the tool, run it, then tell him "Press Refresh tool in the window" and name the branch. Do not ask him to find files or use a browser.
- If a session needs any extra step from him, add it to "Every session" above.
- The window app is `skin/skin-2026-11-12-geodesic-frame/frame_window.py` (uses pywebview, port 8790, up to 8799). Other tools (polyps, lighting) can copy the same pattern: a `*_window.py`, an `install-app.sh`, a Refresh button.
