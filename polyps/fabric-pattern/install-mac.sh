#!/bin/bash
# One-time setup on a Mac for the polyp simulator.
#
# What it does:
#   1. makes a private Python environment in this folder (.venv) and installs the libraries
#   2. registers the simulator to start by itself whenever you log in, and keep running
#   3. opens http://127.0.0.1:8800/ in your browser. Bookmark that link. It is the simulator.
# After that you never need the terminal: the page has a "Get latest changes" button.
# Safe to run again. To remove everything:  bash install-mac.sh --remove
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.coral.polyptool"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

if [ "$1" = "--remove" ]; then
  launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed. The simulator no longer starts at login. (You can delete this folder if you like.)"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 isn't installed. macOS should offer to install the developer tools now."
  echo "Accept that, wait for it to finish, then run this setup again."
  xcode-select --install 2>/dev/null || true
  exit 1
fi

cd "$HERE"
echo "1/3  Setting up Python and the libraries (a few minutes the first time)..."
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

echo "2/3  Making the simulator start at login..."
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$HERE/.venv/bin/python</string>
    <string>$HERE/polyp_tool.py</string>
    <string>--no-browser</string>
  </array>
  <key>WorkingDirectory</key><string>$HERE</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/polyptool.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/polyptool.log</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string></dict>
</dict>
</plist>
PLISTEOF
launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"

echo "3/3  Opening the simulator..."
sleep 4
open "http://127.0.0.1:8800/" || true
echo
echo "Done. The simulator is at  http://127.0.0.1:8800/   (bookmark it)."
echo "If the page doesn't load, wait ten seconds and refresh. Problems? Look at ~/Library/Logs/polyptool.log"
