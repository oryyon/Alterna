#!/usr/bin/env bash
# Construiește Alterna-<versiune>-x86_64.AppImage pentru Linux x86_64.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${VERSION:-$(python3 -c "import sys; sys.path.insert(0, '.'); from app.version import VERSION; print(VERSION)")}"
ARCH="${ARCH:-x86_64}"
APP_NAME="Alterna"
APPIMAGE_NAME="${APP_NAME}-${VERSION}-${ARCH}.AppImage"
WORK="$ROOT/.packaging"
APPDIR="$WORK/${APP_NAME}.AppDir"
DIST="$ROOT/dist"
TOOLS="$WORK/tools"
APPIMAGETOOL_VERSION="continuous-2026-11-06"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL_SHA256="e8c1169c4af66c3184d7ee110713d4be04befe671fa358e2c1591ee840553b03"

command -v python >/dev/null || { echo "Eroare: Python nu este instalat." >&2; exit 1; }
command -v mksquashfs >/dev/null || { echo "Eroare: mksquashfs nu este instalat (instalează squashfs-tools)." >&2; exit 1; }

printf '\n[1/6] Validare catalog\n'
python tools/build_catalog.py

printf '\n[2/6] Verificare dependențe Python\n'
python - <<'PY'
import PyInstaller, PySide6
print("PyInstaller", PyInstaller.__version__)
print("PySide6", PySide6.__version__)
PY

printf '\n[3/6] Build PyInstaller onedir\n'
rm -rf "$ROOT/build" "$DIST/Alterna"
python -m PyInstaller \
  --noconfirm \
  --clean \
  --name "$APP_NAME" \
  --windowed \
  --hidden-import PySide6.QtSvg \
  --collect-all PySide6.QtSvg \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module PySide6.QtWebEngineQuick \
  --exclude-module PySide6.QtQuick \
  --exclude-module PySide6.QtQuick3D \
  --exclude-module PySide6.QtQml \
  --exclude-module PySide6.Qt3DCore \
  --exclude-module PySide6.Qt3DRender \
  --exclude-module PySide6.Qt3DInput \
  --exclude-module PySide6.Qt3DLogic \
  --exclude-module PySide6.Qt3DAnimation \
  --exclude-module PySide6.Qt3DExtras \
  --exclude-module PySide6.QtCharts \
  --exclude-module PySide6.QtDataVisualization \
  --exclude-module PySide6.QtGraphs \
  --exclude-module PySide6.QtBluetooth \
  --exclude-module PySide6.QtNfc \
  --exclude-module PySide6.QtPositioning \
  --exclude-module PySide6.QtMultimedia \
  --exclude-module PySide6.QtMultimediaWidgets \
  --exclude-module PySide6.QtPdf \
  --exclude-module PySide6.QtSql \
  --exclude-module PySide6.QtTest \
  --exclude-module PySide6.QtDesigner \
  --exclude-module PySide6.QtHelp \
  --exclude-module PySide6.QtUiTools \
  --exclude-module PySide6.QtSerialPort \
  --exclude-module PySide6.QtSensors \
  --exclude-module PySide6.QtRemoteObjects \
  --exclude-module PySide6.QtSpatialAudio \
  --exclude-module PySide6.QtTextToSpeech \
  --exclude-module PySide6.QtWebChannel \
  --exclude-module PySide6.QtWebSockets \
  --exclude-module PySide6.scripts \
  --exclude-module PySide6.support \
  --exclude-module PySide6.QtPrintSupport \
  --add-data "$ROOT/data/logos:data/logos" \
  --add-data "$ROOT/app/assets:app/assets" \
  --add-data "$ROOT/catalog.db:." \
  --add-data "$ROOT/LICENSE:." \
  --add-data "$ROOT/LICENSE-DATA:." \
  --add-data "$ROOT/NOTICE:." \
  --distpath "$DIST" \
  --workpath "$ROOT/build" \
  --specpath "$ROOT/build" \
  "$ROOT/packaging/entrypoint.py"

printf '\n[3b/6] Build utilitar selftest (consolă)\n'
python -m PyInstaller \
  --noconfirm \
  --clean \
  --name "${APP_NAME}-selftest" \
  --console \
  --hidden-import PySide6.QtSvg \
  --add-data "$ROOT/data/logos:data/logos" \
  --add-data "$ROOT/catalog.db:." \
  --distpath "$DIST" \
  --workpath "$ROOT/build" \
  --specpath "$ROOT/build" \
  "$ROOT/packaging/selftest_entrypoint.py"

printf '\n[4/6] Pregătire AppDir\n'
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib/alterna" "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/licenses/alterna" "$APPDIR/usr/share/metainfo" \
         "$APPDIR/usr/share/applications" "$TOOLS"
cp -a "$DIST/Alterna/." "$APPDIR/usr/lib/alterna/"
cp "$ROOT/packaging/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp "$ROOT/packaging/alterna.desktop" "$APPDIR/alterna.desktop"
cp "$ROOT/packaging/alterna.desktop" "$APPDIR/usr/share/applications/alterna.desktop"
cp "$ROOT/packaging/alterna.svg" "$APPDIR/alterna.svg"
cp "$ROOT/packaging/alterna.svg" "$APPDIR/usr/share/icons/hicolor/256x256/apps/alterna.svg"
cp "$ROOT/LICENSE" "$ROOT/LICENSE-DATA" "$ROOT/NOTICE" "$APPDIR/usr/share/licenses/alterna/"
cp "$ROOT/packaging/org.alterna.app.appdata.xml" "$APPDIR/usr/share/metainfo/org.alterna.app.appdata.xml"

# appimagetool necesită o pictogramă PNG sau XPM la rădăcina AppDir.
if command -v convert >/dev/null 2>&1; then
  convert -background none "$ROOT/packaging/alterna.svg" -resize 256x256 "$APPDIR/alterna.png"
elif command -v inkscape >/dev/null 2>&1; then
  inkscape "$ROOT/packaging/alterna.svg" --export-type=png \
    --export-filename="$APPDIR/alterna.png" --export-width=256 --export-height=256
else
  echo "Eroare: pentru generarea PNG-ului este necesar ImageMagick sau Inkscape." >&2
  exit 1
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "$APPDIR/alterna.desktop"
fi

printf '\n[5/6] Descărcare appimagetool verificat\n'
TOOL="$TOOLS/appimagetool-x86_64.AppImage"
if [[ ! -f "$TOOL" ]] || ! echo "$APPIMAGETOOL_SHA256  $TOOL" | sha256sum -c - >/dev/null 2>&1; then
  rm -f "$TOOL"
  curl --fail --location --retry 3 --output "$TOOL" "$APPIMAGETOOL_URL"
  echo "$APPIMAGETOOL_SHA256  $TOOL" | sha256sum -c -
fi
chmod +x "$TOOL"

printf '\n[6/6] Creare AppImage\n'
mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/$APPIMAGE_NAME"
rm -f "$OUT"
# --no-appstream: metadata este inclusă în pachet, dar validarea strictă este
# sărită — repository-ul GitHub nu este încă public, deci appstreamcli ar
# eșua pe verificarea de accesibilitate a URL-urilor, nu pe conținut.
# Varianta --appimage-extract-and-run evită dependența de FUSE pe build.
"$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"

printf '\n✔ AppImage creat: %s (%s)\n' "$OUT" "$(du -h "$OUT" | cut -f1)"
