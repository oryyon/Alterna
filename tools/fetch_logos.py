#!/usr/bin/env python3
"""Alterna — descarcă logo-urile aplicațiilor.

Surse, încercate în ordine pentru fiecare aplicație:
1. **Simple Icons** (CDN + raw GitHub) — pictograme de brand, licență CC0;
2. **Wikimedia Commons** (Special:FilePath) — logo-urile oficiale, pentru cele
   retrase/absente din Simple Icons (Adobe, Microsoft, VLC etc.); licențele
   variază — majoritatea mărci înregistrate folosite pentru identificare
   (uz nominal), cele FOSS sub licențe libere.

La succes: salvează în data/logos/<id>.svg|.png și completează câmpul `logo`
în YAML (round-trip, comentariile se păstrează). La eșec: câmpul `logo` rămâne
gol, iar aplicația afișează pictograma provizorie cu inițiale.

Utilizare: python tools/fetch_logos.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from ruamel.yaml import YAML

# Două surse, încercate în ordine (CDN-ul nu deservește slug-urile numerice):
SOURCES = [
    "https://cdn.simpleicons.org/{}",
    "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{}.svg",
]
UA = {"User-Agent": "Alterna-logo-fetch (github.com/alterna-app)"}

# id Alterna → slug Simple Icons (doar unde diferă; verificate pe 2026-11-02 —
# multe branduri, ex. Adobe/VLC/Edge, au fost scoase din Simple Icons la cerere)
SLUG_MAP = {
    "intellij-idea": "intellijidea",
    "eclipse-ide": "eclipseide",
    "chrome": "googlechrome",
    "tor-browser": "torbrowser",
    "jitsi-meet": "jitsi",
    "proton-pass": "proton",
    "obs": "obsstudio",
    "davinci": "davinciresolve",
    "autocad": "autocad",
    "ente-auth": "ente",
    "sevenzip": "7zip",
    "sublime-text": "sublimetext",
}

# id Alterna → nume de fișier pe Wikimedia Commons (confirmate prin sondă
# pe 2026-11-03; se încearcă DOAR dacă Simple Icons nu are pictograma)
WIKIMEDIA = {
    "vlc": "VLC_Icon.svg",
    "chromium": "Chromium Material Icon.svg",
    "vscode": "Visual Studio Code 1.35 icon.svg",
    "photoshop": "Adobe Photoshop CC icon.svg",
    "illustrator": "Adobe Illustrator CC icon.svg",
    "premiere": "Adobe Premiere Pro CC icon.svg",
    "msoffice": "Microsoft Office 2013 logo.svg",
    "edge": "Microsoft Edge logo (2019).svg",
    "virtualbox": "Virtualbox logo.png",
    "openoffice": "OpenOffice.org.svg",
    "geany": "Geany logo.svg",
    "shotcut": "Shotcut logo.svg",
    "openshot": "OpenShot logo.svg",
    "darktable": "Darktable icon.svg",
    "kate": "Breezeicons-apps-48-kate.svg",
    "flameshot": "Flameshot.svg",
    "affinity": "Affinity Photo icon.png",
    "xournalpp": "Xournal++ logo.svg",
    # --- Descoperite in Wikimedia Commons (pilotul de logo-uri) ---
    "avidemux": "Avidemux-logo.png",
    "bleachbit": "Bleachbit logo.svg",
    "calligra": "Calligra-logo.svg",
    "deadbeef": "DeadbeefLOGO.png",
    "elisa": "Elisa logo 2000.svg",
    "fl-studio": "FL Studio Logo Wordmark.svg",
    "fusion360": "Fusion 360 Logo.png",
    "gparted": "Scalable gparted.svg",
    "kazam": "KAZAM Logo.svg",
    "librecad": "LibreCAD-Logo.png",
    "peazip": "Peazip ico.svg",
    "stacer": "Biglinux-Icons \u2013 stacer 1.svg",
    "standard-notes": "Standard Notes - Icon.png",
    "sweet-home-3d": "Sweet Home 3D - AboutIcon.png",
    "tenacity": "Tenacity logo.jpg",
    "timeshift": "Biglinux-Icons \u2013 timeshift.svg",
    "ventoy": "Ventoy Logo.png",
    "zed": "Zed Editor Logo.png",
    "pinta": "Pinta.png",
    "winrar": "WinRAR icon.svg",
    "ssr": "Biglinux-Icons \u2013 simplescreenrecorder.svg",
    "vokoscreenng": "Breezeicons-apps-48-vokoscreen.svg",
    "wps": "Deepin Icon Theme \u2013 application-wps-office.wps.svg",
    # logo-ul oficial al proiectului (GPL, autor: Charles Barcza)
    "smplayer": "SMPlayer icon.png",
}
WIKIMEDIA_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=256"


def fetch(url: str, timeout: int = 20) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout).read()
    except Exception:
        return None


def extensie(data: bytes) -> str | None:
    """Detectează formatul imaginii după conținut."""
    if b"<svg" in data[:500]:
        return "svg"
    if data.startswith(b"\x89PNG"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    return None


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=root / "data")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    apps_dir = args.data / "apps"
    logos_dir = args.data / "logos"
    logos_dir.mkdir(exist_ok=True)

    yaml = YAML()
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True
    yaml.width = 4096

    ok, missing = [], []
    for path in sorted(apps_dir.glob("*.yaml")):
        app = yaml.load(path.read_text(encoding="utf-8"))
        app_id = app.get("id", path.stem)
        slug = SLUG_MAP.get(app_id, app_id.replace("_", ""))

        # 1. Simple Icons (CDN + raw GitHub)
        data = next((d for d in (fetch(s.format(slug)) for s in SOURCES)
                     if d and extensie(d) == "svg"), None)
        ext = "svg" if data else None

        # 2. Wikimedia Commons (doar pentru cele fără pictogramă în Simple Icons)
        if data is None and app_id in WIKIMEDIA:
            import urllib.parse
            d = fetch(WIKIMEDIA_URL.format(
                urllib.parse.quote(WIKIMEDIA[app_id])))
            if d and extensie(d):
                data, ext = d, extensie(d)

        if data is None:
            missing.append(app_id)
            # curățăm un câmp logo rămas spre un fișier inexistent
            if app.get("logo") and not (args.data / app["logo"]).exists():
                del app["logo"]
                if not args.dry_run:
                    with path.open("w", encoding="utf-8") as fh:
                        yaml.dump(app, fh)
            continue
        ok.append(app_id)
        if args.dry_run:
            continue
        rel = f"logos/{app_id}.{ext}"
        (logos_dir / f"{app_id}.{ext}").write_bytes(data)
        if app.get("logo") != rel:
            app["logo"] = rel
            with path.open("w", encoding="utf-8") as fh:
                yaml.dump(app, fh)

    print(f"✔ logo-uri descărcate: {len(ok)}")
    print(f"— fără pictogramă în Simple Icons ({len(missing)}), rămân inițialele: "
          + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
