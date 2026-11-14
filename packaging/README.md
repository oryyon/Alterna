# Distribuție Linux

Proiectul produce două pachete independente din aceeași sursă:

| Format | Fișier | Instalare |
|---|---|---|
| AppImage | `Alterna-<versiune>-x86_64.AppImage` | executabil, chmod +x |
| Debian | `alterna_<versiune>-1_amd64.deb` | `sudo apt install ./alterna_*.deb` |

Versiunea provine din `app/version.py` — sursă unică de adevăr folosită de
ambele pipeline-uri și de metadata pachetului.

## Pachet Debian

```bash
./packaging/build_deb.sh
```

Rezultatul este `dist/alterna_<versiune>-1_amd64.deb`.

Structura respectă Debian Policy:

```text
/opt/alterna/                        aplicația și resursele
/usr/share/applications/alterna.desktop
/usr/share/icons/hicolor/{16..256}x*/apps/alterna.png
/usr/share/icons/hicolor/scalable/apps/alterna.svg
/usr/share/metainfo/org.alterna.app.appdata.xml
/usr/share/doc/alterna/{README.md.gz,CONTRIBUTING.md.gz,copyright,...}
/DEBIAN/{control,postinst,prerm}
```

Validarea include `dpkg-deb --info` și `lintian`. Pachetul este construit cu
`dpkg-deb --root-owner-group`, deci nu are nevoie de `fakeroot` la runtime.

### Testarea pachetului

```bash
rm -rf /tmp/debtest && mkdir -p /tmp/debtest
dpkg-deb --extract dist/alterna_*.deb /tmp/debtest
QT_QPA_PLATFORM=offscreen /tmp/debtest/opt/alterna/alterna --version
QT_QPA_PLATFORM=offscreen /tmp/debtest/opt/alterna/alterna --selftest
```

## AppImage

Buildul complet, pe Ubuntu 24.04 x86_64:

```bash
./packaging/build_appimage.sh
```

Rezultatul este `Alterna-0.1.0-x86_64.AppImage` în rădăcina proiectului.

Scriptul:

1. reconstruiește și validează catalogul SQLite;
2. construiește aplicația cu PyInstaller în format `onedir`;
3. construiește separat utilitarul `Alterna-selftest` (cu consolă);
4. creează AppDir-ul cu `AppRun`, metadata `.desktop`, metadata AppStream,
   pictogramă și licențe;
5. descarcă `appimagetool` numai după verificarea SHA-256;
6. creează AppImage-ul fără a necesita FUSE pe mașina de build.

### Dimensiune

Bundle-ul este restrâns explicit la modulele Qt necesare (`QtCore`, `QtGui`,
`QtWidgets`, `QtSvg`), fără `--collect-all PySide6`. O variantă care împachetează
tot PySide6 produce un AppImage de ~257 MB; pipeline-ul curent produce ~63 MB.

### Dependențe de build

```bash
sudo apt install squashfs-tools desktop-file-utils imagemagick
python -m pip install -r requirements.txt
```

`curl` este folosit pentru descărcarea verificată a `appimagetool`.

## Testarea pachetului

Verificare rapidă a resurselor incluse în bundle:

```bash
./Alterna-0.1.0-x86_64.AppImage --appimage-extract-and-run --selftest
```

Ieșire așteptată:

```text
resurse: .../squashfs-root/usr/lib/alterna/_internal
catalog: .../catalog.db (există: True)
aplicatii: 100
categorii: 13
logo-uri: 73 fișiere, 72 aplicații cu logo
REZULTAT: OK
```

Pentru testare completă, fișierul poate fi extras și executat prin AppDir:

```bash
./Alterna-0.1.0-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun --selftest
```

Test grafic fără ecran (mediu CI):

```bash
QT_QPA_PLATFORM=offscreen timeout 8 ./squashfs-root/AppRun
```

Buildul produce și `dist/Alterna-selftest/Alterna-selftest`, o versiune cu
consolă a verificării, utilă în CI.

## Compatibilitate

Buildul este reproductibil pe Ubuntu 24.04 x86_64 și integrează bibliotecile Qt
din mediul de build. Testarea pe alte distribuții este necesară înainte de
publicarea unor release-uri generale.
