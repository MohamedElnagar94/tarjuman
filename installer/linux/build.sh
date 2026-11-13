#!/usr/bin/env bash
# Builds Tarjuman-<version>-x86_64.AppImage: one file with its own Python, every package, the built
# web app and the browser extension. A Linux user needs neither Python nor Node.js.
#
#   installer/linux/build.sh            (needs curl, python3 and Node.js 20+ on the building machine)
#   SKIP_WEB=1 installer/linux/build.sh (reuse frontend/dist and extension/dist already built)
#
# Output: build/linux/Tarjuman-<version>-x86_64.AppImage and its .sha256
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${OUT:-$ROOT/build/linux}"
APPDIR="$OUT/Tarjuman.AppDir"
CACHE="$OUT/cache"
PY_MINOR="${PY_MINOR:-3.13}"
rm -rf "$APPDIR"
mkdir -p "$APPDIR" "$CACHE"

# 1) Python itself: a relocatable build from python-build-standalone (the newest 3.13 for x86_64 Linux,
#    without debug symbols).
url="$(curl -fsSL https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest | python3 -c '
import json, re, sys
minor = sys.argv[1]
assets = json.load(sys.stdin)["assets"]
# Match the file name: in the download address the "+" is written %2B.
pat = re.compile(rf"^cpython-{re.escape(minor)}\.\d+\+\d+-x86_64-unknown-linux-gnu-install_only_stripped\.tar\.gz$")
print(next(a["browser_download_url"] for a in assets if pat.match(a["name"])))
' "$PY_MINOR")"
tarball="$CACHE/$(basename "$url")"
[ -f "$tarball" ] || curl -fsSL "$url" -o "$tarball"
tar -xzf "$tarball" -C "$APPDIR"   # -> python/
PY="$APPDIR/python/bin/python3"
echo "Bundling $("$PY" -c 'import platform; print(platform.python_version())') from $(basename "$url")"

# 2) Every Python package, inside that Python.
"$PY" -m pip install --disable-pip-version-check --no-warn-script-location -q -r "$ROOT/backend/requirements.txt"
# The AppImage is read-only, so pip could never change it afterwards: it only takes room.
"$PY" -m pip uninstall -y -q pip

# 3) Tarjuman's own code.
mkdir -p "$APPDIR/backend" "$APPDIR/shared/dub-engine" "$APPDIR/assets"
cp -r "$ROOT/backend/tarjuman" "$APPDIR/backend/tarjuman"
cp "$ROOT/backend/requirements.txt" "$APPDIR/backend/"
cp -r "$ROOT/shared/dub-engine/src" "$APPDIR/shared/dub-engine/src"
cp -r "$ROOT/assets/brand" "$APPDIR/assets/brand"
cp "$ROOT/.env.example" "$ROOT/README.md" "$APPDIR/"
cp "$ROOT/LICENSE" "$APPDIR/LICENSE.txt"
# Marks the installed app: its data then lives in ~/.local/share/Tarjuman (the AppImage is read-only).
echo "Tarjuman, installed. Data: \$XDG_DATA_HOME/Tarjuman (~/.local/share/Tarjuman)" > "$APPDIR/installed.txt"

# 4) The web app and the extension, built.
if [ -z "${SKIP_WEB:-}" ]; then
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund && npm run build)
  (cd "$ROOT/extension" && npm ci --no-audit --no-fund && npm run build)
fi
mkdir -p "$APPDIR/frontend"
cp -r "$ROOT/frontend/dist" "$APPDIR/frontend/dist"
cp -r "$ROOT/extension/dist" "$APPDIR/extension"

# 5) What makes it an AppImage: the entry script, the menu entry and the icon.
install -m 755 "$ROOT/installer/linux/AppRun" "$APPDIR/AppRun"
cp "$ROOT/installer/linux/tarjuman.desktop" "$APPDIR/tarjuman.desktop"
cp "$ROOT/assets/brand/icon-256.png" "$APPDIR/tarjuman.png"
ln -sf tarjuman.png "$APPDIR/.DirIcon"

# 6) Compiled ahead, so the first start doesn't spend minutes compiling; then a check that it imports.
find "$APPDIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
"$PY" -m compileall -q -j 0 "$APPDIR/python/lib" "$APPDIR/backend" > /dev/null || true
PYTHONPATH="$APPDIR/backend" "$PY" -c "import fastapi, uvicorn, faster_whisper, onnxruntime, tarjuman.api.app"
PYTHONPATH="$APPDIR/backend" "$PY" -m tarjuman --version > /dev/null

# 7) One file. appimagetool is itself an AppImage; extract-and-run works where FUSE doesn't (CI, WSL).
version="$(PYTHONPATH="$APPDIR/backend" "$PY" -c 'import tarjuman; print(tarjuman.__version__)')"
tool="$CACHE/appimagetool-x86_64.AppImage"
[ -f "$tool" ] || curl -fsSL https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -o "$tool"
chmod +x "$tool"
image="$OUT/Tarjuman-$version-x86_64.AppImage"
rm -f "$image"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream "$APPDIR" "$image" > "$CACHE/appimagetool.log" 2>&1 \
  || { tail -30 "$CACHE/appimagetool.log"; exit 1; }
(cd "$OUT" && sha256sum "$(basename "$image")" > "$(basename "$image").sha256")
echo "Built $image ($(du -m "$image" | cut -f1) MB)"
