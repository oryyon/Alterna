#!/usr/bin/env bash
# Construiește pachetul Debian (.deb) pentru Alterna.
#
# Structura respectă Debian Policy:
#   /opt/alterna/             — aplicația și resursele sale
#   /usr/share/applications/  — intrarea din meniul aplicațiilor
#   /usr/share/icons/hicolor/ — pictogramele la dimensiunile standard
#   /usr/share/metainfo/      — metadata AppStream
#   /usr/share/doc/alterna/   — README, licențe, changelog, copyright
#   DEBIAN/                   — control, postinst, prerm
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PACKAGE="alterna"
ARCH="amd64"
REVISION="${REVISION:-1}"
WORK="$ROOT/.packaging/deb"
DEB_ROOT="$WORK/${PACKAGE}_${REVISION}"
DIST="$ROOT/dist"

for tool in dpkg-deb fakeroot; do
  command -v "$tool" >/dev/null || {
    echo "Eroare: $tool nu este instalat (instalează dpkg-dev / fakeroot)." >&2
    exit 1
  }
done

PYTHON_BIN=".venv/bin/python"
[[ -x "$PYTHON_BIN" ]] || PYTHON_BIN="python3"

# Versiunea provine din app/version.py — sursă unică de adevăr.
APP_VERSION="$("$PYTHON_BIN" -c "from app.version import VERSION; print(VERSION)")"
DEB_VERSION="${APP_VERSION}-${REVISION}"

printf '\n[1/7] Validare catalog\n'
"$PYTHON_BIN" tools/build_catalog.py

printf '\n[2/7] Build PyInstaller onedir\n'
rm -rf "$ROOT/build" "$DIST/$PACKAGE"
"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --name "$PACKAGE" \
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

printf '\n[3/7] Asamblare arbore Debian\n'
rm -rf "$DEB_ROOT"
mkdir -p "$DEB_ROOT/DEBIAN" \
         "$DEB_ROOT/opt/$PACKAGE" \
         "$DEB_ROOT/usr/bin" \
         "$DEB_ROOT/usr/share/applications" \
         "$DEB_ROOT/usr/share/metainfo" \
         "$DEB_ROOT/usr/share/man/man1" \
         "$DEB_ROOT/usr/share/doc/$PACKAGE"
cp -a "$DIST/$PACKAGE/." "$DEB_ROOT/opt/$PACKAGE/"

# Launcher în /usr/bin — aplicația stă în /opt, dar trebuie să fie în PATH
# pentru terminal și pentru Exec=alterna din desktop entry.
cp "$ROOT/packaging/alterna-launcher" "$DEB_ROOT/usr/bin/$PACKAGE"
chmod 755 "$DEB_ROOT/usr/bin/$PACKAGE"

cp "$ROOT/packaging/alterna.desktop" "$DEB_ROOT/usr/share/applications/"
cp "$ROOT/packaging/org.alterna.app.appdata.xml" \
   "$DEB_ROOT/usr/share/metainfo/org.alterna.app.appdata.xml"

# Pagină de manual, pentru integrarea completă în sistem.
mkdir -p "$DEB_ROOT/usr/share/man/man1"
cp "$ROOT/packaging/alterna.1" "$DEB_ROOT/usr/share/man/man1/$PACKAGE.1"
# Pagina de manual se distribuie comprimată (altfel lintian: uncompressed-manual-page)
gzip -9nf "$DEB_ROOT/usr/share/man/man1/$PACKAGE.1"

cp "$ROOT/README.md" "$DEB_ROOT/usr/share/doc/$PACKAGE/README.md"
cp "$ROOT/CONTRIBUTING.md" "$DEB_ROOT/usr/share/doc/$PACKAGE/CONTRIBUTING.md"
cp "$ROOT/LICENSE" "$DEB_ROOT/usr/share/doc/$PACKAGE/copyright"
cp "$ROOT/LICENSE-DATA" "$DEB_ROOT/usr/share/doc/$PACKAGE/LICENSE-DATA"
cp "$ROOT/NOTICE" "$DEB_ROOT/usr/share/doc/$PACKAGE/NOTICE"
for doc in README.md CONTRIBUTING.md LICENSE-DATA NOTICE; do
  # -n: nu include timestamp-ul buildului în arhiva gzip.
  gzip -9nf "$DEB_ROOT/usr/share/doc/$PACKAGE/$doc"
done

printf '\n[4/7] Pictograme\n'
SVG="$ROOT/packaging/alterna.svg"
for size in 16 22 24 32 48 64 128 256; do
  dir="$DEB_ROOT/usr/share/icons/hicolor/${size}x${size}/apps"
  mkdir -p "$dir"
  convert -background none "$SVG" -resize "${size}x${size}" "$dir/$PACKAGE.png"
done
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps"
cp "$SVG" "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/$PACKAGE.svg"

printf '\n[5/7] Metadata DEBIAN\n'

# Normalizare permisiuni: fișierele copiate din mediul de build pot avea
# 0664/0775, iar Debian Policy cere 0644 pentru date și 0755 pentru
# directoare. dpkg-deb --root-owner-group nu corectează permisiunile.
find "$DEB_ROOT/opt" -type d -exec chmod 755 {} +
find "$DEB_ROOT/opt" -type f -exec chmod 644 {} +
# Binarele din bundle (executable, shiboken) trebuie să rămână executabile.
# Ordinea contează: întâi se marchează executabilele, apoi se fixează
# permisiunile bibliotecilor partajate.
find "$DEB_ROOT/opt" -type f -perm -u+x ! -name '*.so' ! -name '*.so.*' \
  -exec chmod 755 {} +
# Bibliotecile partajate nu sunt executabile (Debian Policy 10.1): dlopen nu
# are nevoie de bitul de execuție, iar lintian cere 0644 pentru ele.
find "$DEB_ROOT/opt" -type f \( -name '*.so' -o -name '*.so.*' \) \
  -exec chmod 644 {} +
# Executabilul principal al aplicației.
chmod 755 "$DEB_ROOT/opt/$PACKAGE/$PACKAGE"
find "$DEB_ROOT/usr" -type d -exec chmod 755 {} +
find "$DEB_ROOT/usr" -type f -exec chmod 644 {} +
chmod 755 "$DEB_ROOT/usr/bin/$PACKAGE"

INSTALLED_SIZE=$(du -sk "$DEB_ROOT" | cut -f1)
CONTROL="$DEB_ROOT/DEBIAN/control"

cat > "$CONTROL" <<EOF
Package: $PACKAGE
Version: $DEB_VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: libc6 (>= 2.34), libegl1
Recommends: fonts-noto-core, libglib2.0-0t64 | libglib2.0-0
Installed-Size: $INSTALLED_SIZE
Maintainer: Alterna contributors <alterna@users.noreply.github.com>
Homepage: https://github.com/oryyon/Alterna
Description: catalog de alternative software pentru Linux
 Alterna este o aplicație desktop pentru descoperirea de alternative la
 programe software, cu un catalog local în limba română.
 .
 Funcționalități:
  - căutare live și filtre pe categorie, licență, platformă și preț;
  - comparare între până la patru aplicații, cu matrice de funcționalități;
  - export al comparațiilor în Markdown, CSV, HTML, TXT și JSON;
  - indicatori obiectivi (popcon, stele GitHub, ultima versiune) cu surse;
  - funcționare complet offline: datele sunt stocate local în SQLite.
EOF

cat > "$DEB_ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

case "$1" in
  configure)
    if command -v update-desktop-database >/dev/null 2>&1; then
      update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
      gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    fi
    ;;
esac

exit 0
EOF

cat > "$DEB_ROOT/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e

case "$1" in
  remove|deconfigure)
    if command -v update-desktop-database >/dev/null 2>&1; then
      update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
      gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    fi
    ;;
esac

exit 0
EOF

chmod 755 "$DEB_ROOT/DEBIAN/postinst" "$DEB_ROOT/DEBIAN/prerm"
chmod 644 "$CONTROL"

printf '\n[6/7] Construire pachet\n'
OUT="$DIST/${PACKAGE}_${DEB_VERSION}_${ARCH}.deb"
rm -f "$OUT"
fakeroot dpkg-deb --root-owner-group --build "$DEB_ROOT" "$OUT" >/dev/null
chmod 644 "$OUT"

printf '\n[7/7] Validare\n'
dpkg-deb --info "$OUT" | sed -n '2,12p'

# Verificare de consistență: versiunea raportată de binarul împachetat trebuie
# să coincidă cu cea din sursă. Fără asta, un bytecode vechi sau un build
# rulat înainte de schimbarea versiunii ar trece neobservat.
BUILT_VER="$(QT_QPA_PLATFORM=offscreen "$DEB_ROOT/opt/$PACKAGE/$PACKAGE" --version 2>/dev/null | awk '{print $2}')"
if [ "$BUILT_VER" != "$APP_VERSION" ]; then
  echo "Eroare: binarul împachetat raportează versiunea '$BUILT_VER'," >&2
  echo "       dar sursa indică '$APP_VERSION'. Buildul este inconsistent." >&2
  exit 1
fi
echo "✔ versiune consistentă: $BUILT_VER"

if command -v lintian >/dev/null 2>&1; then
  echo '--- lintian ---'
  lintian --no-tag-display-limit "$OUT" || true
fi

printf '\n✔ Pachet creat: %s (%s)\n' "$OUT" "$(du -h "$OUT" | cut -f1)"
