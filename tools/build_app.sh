#!/usr/bin/env bash
# Build the "Lifeboard.app" Dock app into ~/Applications.
# Generates the icon (.icns) from app/icon_1024.png and assembles the bundle.
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
APPNAME="Lifeboard"
APP="$HOME/Applications/$APPNAME.app"
PNG="$DIR/app/icon_1024.png"
ICONSET="$DIR/app/$APPNAME.iconset"
ICNS="$DIR/app/icon.icns"

# 1) Icon
"$DIR/.venv/bin/python" "$DIR/tools/make_icon.py"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$PNG" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s*2)); sips -z $d $d "$PNG" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ICNS"
rm -rf "$ICONSET"

# 2) Bundle
mkdir -p "$HOME/Applications"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$DIR/app/Info.plist" "$APP/Contents/Info.plist"
cp "$DIR/app/launcher"   "$APP/Contents/MacOS/launcher"
chmod +x "$APP/Contents/MacOS/launcher"
cp "$ICNS" "$APP/Contents/Resources/icon.icns"
touch "$APP"  # nudge the icon cache

echo "Built $APP"
