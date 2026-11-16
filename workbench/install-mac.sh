#!/bin/bash
# One-time setup on a Mac for the workbench (the viewer with Skin / Polyp / Combined tabs).
#
# What it does:
#   1. makes its OWN copy of the repo in ~/coral-workbench (separate from ~/coral-simulator),
#      so the workbench never moves when the simulators switch branch
#   2. registers the workbench to start at login and keep running
#   3. opens http://127.0.0.1:8840/   (bookmark it)
# The workbench needs only the Python that macOS already has: nothing to install.
# Safe to run again. To remove:  bash install-mac.sh --remove
set -e
BRANCH="${1:-workbench-2026-11-15-viewer}"   # after the pull request is merged, use: bash install-mac.sh main
DIR="$HOME/coral-workbench"
LABEL="com.coral.workbench"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

if [ "$1" = "--remove" ]; then
  launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"; echo "Removed. (You can delete $DIR if you like.)"; exit 0
fi
command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 || { echo "Needs git and Python 3: macOS should offer to install the developer tools now. Accept, then run this again."; xcode-select --install 2>/dev/null || true; exit 1; }

echo "1/3  Getting the repo (branch $BRANCH)..."
if [ -d "$DIR/.git" ]; then git -C "$DIR" fetch --prune origin; else git clone https://github.com/RemyOP-LTL/Inflatable-Coral.git "$DIR"; fi
git -C "$DIR" checkout -B "$BRANCH" "origin/$BRANCH"

echo "2/3  Making the workbench start at login..."
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/usr/bin/python3</string><string>$DIR/workbench/workbench.py</string><string>--no-browser</string></array>
  <key>WorkingDirectory</key><string>$DIR/workbench</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/workbench.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/workbench.log</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string></dict>
</dict></plist>
PLISTEOF
launchctl bootout "$DOMAIN" "$PLIST" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"

echo "3/3  Opening the workbench..."
sleep 3; open "http://127.0.0.1:8840/" || true
echo; echo "Done: http://127.0.0.1:8840/  (bookmark it). Problems? See ~/Library/Logs/workbench.log"
