#!/bin/bash
# One-time setup: makes a "Sea Anemone" app in your Applications folder (you can drag it to the Dock).
#
# What it does:
#   1. makes a private Python folder (.venv) here and installs the libraries the tool needs
#   2. makes ~/Applications/Sea Anemone.app (with the sea anemone icon), which opens the tool in its own window
# Safe to run again (do that if you ever move this repo folder). To remove: delete the app and the .venv folder.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Sea Anemone.app"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 isn't installed. macOS should offer to install the developer tools now."
  xcode-select --install 2>/dev/null || true
  exit 1
fi

cd "$HERE"
echo "1/2  Setting up Python and the libraries (a minute or two the first time)..."
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

echo "2/2  Making the app..."
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$HERE/icon/sea-anemone.icns" "$APP/Contents/Resources/sea-anemone.icns"
cat > "$APP/Contents/Info.plist" <<'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Sea Anemone</string>
  <key>CFBundleDisplayName</key><string>Sea Anemone</string>
  <key>CFBundleIdentifier</key><string>com.coral.seaanemone</string>
  <key>CFBundleExecutable</key><string>run</string>
  <key>CFBundleIconFile</key><string>sea-anemone</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSUIElement</key><false/>
</dict></plist>
PLISTEOF
cat > "$APP/Contents/MacOS/run" <<RUNEOF
#!/bin/bash
cd "$HERE"
exec "$HERE/.venv/bin/python" anemone_window.py >> "\$HOME/Library/Logs/sea-anemone.log" 2>&1
RUNEOF
chmod +x "$APP/Contents/MacOS/run"
touch "$APP"

echo
echo "Done. Opening it now. To keep it in the Dock: right-click its Dock icon, Options, Keep in Dock."
echo "Its home: $APP"
open "$APP"
