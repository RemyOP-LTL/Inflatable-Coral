#!/bin/bash
# Double-click this file to start the polyp tool. The first time, it sets itself up (a few minutes).
# After that it starts in a few seconds. Close this window (or press Ctrl+C) to stop the tool.
cd "$(dirname "$0")" || exit 1
pause() { echo; read -r -p "Press Return to close this window. "; }

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 isn't installed. macOS should offer to install the developer tools now."
  echo "Accept that, wait for it to finish, then double-click this file again."
  xcode-select --install 2>/dev/null
  pause; exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "First-time setup: creating a private Python environment..."
  python3 -m venv .venv || { echo "Couldn't create the environment."; pause; exit 1; }
fi
PY=.venv/bin/python

if ! "$PY" -c "import numpy, scipy, matplotlib, shapely" >/dev/null 2>&1; then
  echo "First-time setup: downloading the libraries (a few minutes, only this once)..."
  "$PY" -m pip install --quiet --upgrade pip &&
  "$PY" -m pip install --quiet numpy scipy matplotlib shapely ||
    { echo "The install failed. Check your internet connection and try again."; pause; exit 1; }
fi

echo "Starting the polyp tool. Your web browser will open in a moment..."
"$PY" polyp_tool.py
pause
