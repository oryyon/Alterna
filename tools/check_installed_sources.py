#!/usr/bin/env python3
"""Alterna — verifică sursele de instalare ale aplicațiilor (punctul 16).

Detectarea „✓ instalat” (vezi `app/installed.py`) are nevoie ca fiecare
aplicație să știe **cum** se instalează: pachet Debian, snap sau Flatpak.
Numele lor se verifică contra registrelor oficiale:

- **snap** — `snapcraft.io/<nume>` (magazinul oficial Canonical);
- **flatpak** — `flathub.org/api/v2/appstream/<app-id>` (API-ul Flathub).

Regula: eu *propun* numele, sursa oficială *confirmă*. Ce nu există în
registru nu se scrie în catalog — altfel am detecta instalări inexistente.

Fișierele YAML sunt rescrise in-place cu ruamel.yaml (round-trip), deci
comentariile se păstrează.

Utilizare:
    python tools/check_installed_sources.py --dry-run   # doar raportul
    python tools/check_installed_sources.py             # scrie în YAML
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}

#: Cache local al verificărilor (registrele se interoghează rar).
CACHE = Path.home() / ".cache" / "alterna" / "surse-instalare.json"

#: Numele snap candidate: id aplicație → nume snap (prima variantă care există
#: în magazinul oficial câștigă).
SNAP_CANDIDATI: dict[str, tuple[str, ...]] = {
    "vscode": ("code",), "vscodium": ("vscodium",),
    "signal": ("signal-desktop",), "telegram": ("telegram-desktop",),
    "obs": ("obs-studio",), "chromium": ("chromium",),
    "firefox": ("firefox",), "thunderbird": ("thunderbird",),
    "spotify": ("spotify",), "discord": ("discord",),
    "sublime-text": ("sublime-text",), "wps": ("wps-office",),
    "davinci": ("davinci-resolve",),
    "onlyoffice": ("onlyoffice-desktopeditors",), "zoom": ("zoom-client",),
    "fl-studio": ("fl-studio",), "autocad": ("autocad",),
    "fusion360": ("fusion360",), "notion": ("notion-desktop",),
    "obsidian": ("obsidian",), "element": ("element-desktop",),
    "joplin": ("joplin-desktop",), "logseq": ("logseq",),
    "standard-notes": ("standard-notes",), "simplenote": ("simplenote",),
    "qbittorrent": ("qbittorrent",), "keepassxc": ("keepassxc",),
    "bitwarden": ("bitwarden",), "1password": ("1password",),
    "proton-pass": ("proton-pass",), "figma": ("figma-linux",),
    "opera": ("opera",), "edge": ("microsoft-edge",),
    "msoffice": ("microsoft-office",), "libreoffice": ("libreoffice",),
    "openoffice": ("openoffice",), "intellij-idea": ("intellij-idea-community",),
    "pycharm": ("pycharm-community",), "eclipse-ide": ("eclipse",),
    "gimp": ("gimp",), "inkscape": ("inkscape",), "krita": ("krita",),
    "kdenlive": ("kdenlive",), "vlc": ("vlc",), "blender": ("blender",),
    "audacity": ("audacity",), "darktable": ("darktable",),
    "openscad": ("openscad",), "openshot": ("openshot",),
    "shotcut": ("shotcut",), "mpv": ("mpv",),
}


#: ID-uri Flatpak candidate: id aplicație → app ID (prima variantă confirmată
#: de API-ul Flathub câștigă).
FLATPAK_CANDIDATI: dict[str, tuple[str, ...]] = {
    "gimp": ("org.gimp.GIMP",), "inkscape": ("org.inkscape.Inkscape",),
    "krita": ("org.kde.krita",), "kdenlive": ("org.kde.kdenlive",),
    "kate": ("org.kde.kate",), "vlc": ("org.videolan.VLC",),
    "blender": ("org.blender.Blender",), "firefox": ("org.mozilla.firefox",),
    "thunderbird": ("org.mozilla.Thunderbird",),
    "chromium": ("org.chromium.Chromium",), "spotify": ("com.spotify.Client",),
    "signal": ("org.signal.Signal",), "discord": ("com.discordapp.Discord",),
    "element": ("im.riot.Riot",), "joplin": ("net.cozic.joplin_desktop",),
    "obsidian": ("md.obsidian.Obsidian",),
    "tor-browser": ("org.torproject.tor-browser-launcher",),
    "telegram": ("org.telegram.desktop",),
    "audacity": ("com.audacityteam.Audacity",),
    "davinci": ("com.blackmagicdesign.DaVinciResolve",),
    "onlyoffice": ("org.onlyoffice.desktopeditors",),
    "darktable": ("org.darktable.Darktable",), "lmms": ("org.lmms.LMMS",),
    "mpv": ("io.mpv.Mpv",), "neovim": ("io.neovim.neovim",),
    "keepassxc": ("org.keepassxc.KeePassXC",),
    "bitwarden": ("com.bitwarden.desktop",),
    "1password": ("com.1password.1password",),
    "proton-pass": ("com.protonpass.pass",), "zed": ("dev.zed.Zed",),
    "syncthing": ("org.syncthing.syncthing",),
    "bleachbit": ("org.bleachbit.BleachBit",),
    "timeshift": ("com.linuxmint.timeshift",),
    "filezilla": ("org.filezillaproject.Filezilla",),
    "xournalpp": ("io.github.xournalpp.xournalpp",),
    "pinta": ("com.github.PintaProject.Pinta",),
    "cherrytree": ("com.giuspen.cherrytree",),
    "tenacity": ("org.tenacityaudio.Tenacity",),
    "strawberry": ("org.strawberrymusicplayer.strawberry",),
    "elisa": ("org.kde.elisa",), "calligra": ("org.kde.calligra",),
    "gparted": ("org.gnome.gparted",),
    "flameshot": ("org.flameshot.Flameshot",),
    "copyq": ("io.github.hluk.CopyQ",), "obs": ("com.obsproject.Studio",),
    "penpot": ("com.getoutline.Penpot",),
    "deadbeef": ("org.deadbeef.DeadaB33f",),
    "vokoscreenng": ("com.github.vokoscreenNG.VokoscreenNG",),
}


def citește_json(url: str, timeout: int = 20) -> dict | None:
    """GET JSON; None la orice eșec."""
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=timeout) as răspuns:
            if răspuns.status != 200:
                return None
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def citește_text(url: str, timeout: int = 20) -> str:
    """GET text; șirul gol la orice eșec."""
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=timeout) as răspuns:
            if răspuns.status != 200:
                return ""
            return răspuns.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError):
        return ""



def exista_snap(nume: str, cache: dict) -> bool:
    """Verifică în magazinul oficial: pagina există și nu e un 404."""
    if nume in cache:
        return bool(cache[nume])
    pagină = citește_text(f"https://snapcraft.io/{nume}")
    ok = ("Snap Store" in pagină and "404" not in pagină[:4000]
          and "UNOFFICIAL" not in pagină[:4000])
    cache[f"snap:{nume}"] = ok
    return ok


def exista_flatpak(app_id: str, cache: dict) -> bool:
    """Verifică în API-ul Flathub: aplicația există."""
    cheie = f"flatpak:{app_id}"
    if cheie in cache:
        return bool(cache[cheie])
    date = citește_json(f"https://flathub.org/api/v2/appstream/{app_id}")
    ok = bool(date) and bool(date.get("id") or date.get("name"))
    cache[cheie] = ok
    return ok


def încarcă_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {}


def salvează_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False),
                     encoding="utf-8")


def muta_langat(dicționar, cheie: str, după: str) -> None:
    """Mută o cheie imediat după alta (ruamel păstrează ordinea din fișier)."""
    if cheie not in dicționar:
        return
    valoare = dicționar[cheie]
    del dicționar[cheie]
    poziție = 0
    for i, existent in enumerate(dicționar):
        if existent == după:
            poziție = i + 1
            break
    dicționar.insert(poziție, cheie, valoare)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="afișează schimbările fără a scrie fișierele")
    args = parser.parse_args()

    cache = încarcă_cache()
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    snapuri: list[tuple[str, str]] = []
    flatpakuri: list[tuple[str, str]] = []
    apps_citite: list[tuple[Path, dict]] = []
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        if not isinstance(app, dict):
            continue
        app_id = app.get("id", cale.stem)
        apps_citite.append((cale, app))

        # --- snap ---------------------------------------------------------------
        if not app.get("snap"):
            pachet = app.get("package") or app_id
            for candidat in SNAP_CANDIDATI.get(app_id, (pachet,)):
                if candidat and exista_snap(candidat, cache):
                    snapuri.append((app_id, candidat))
                    app["snap"] = candidat
                    break

        # --- flatpak ------------------------------------------------------------
        if not app.get("flatpak"):
            for candidat in FLATPAK_CANDIDATI.get(app_id, ()):
                if exista_flatpak(candidat, cache):
                    flatpakuri.append((app_id, candidat))
                    app["flatpak"] = candidat
                    break

        # Cheile de instalare stau lângă `package`, nu la sfârșitul fișierului.
        ancoră = "package" if "package" in app else "website"
        for cheie in ("snap", "flatpak"):
            if app.get(cheie):
                muta_langat(app, cheie, ancoră)
                ancoră = cheie

        if not args.dry_run and (app.get("snap") or app.get("flatpak")):
            with cale.open("w", encoding="utf-8") as fh:
                yaml.dump(app, fh)

    salvează_cache(cache)
    # Raportul arată starea finală (nu doar ce s-a scris acum): o aplicație
    # deja confirmată la o rulare anterioară rămâne confirmată.
    toate_snap = sorted((app_id, app.get("snap")) for app_id, app in
                        ((a.get("id", c.stem), a) for c, a in apps_citite)
                        if app.get("snap"))
    toate_flatpak = sorted((app_id, app.get("flatpak")) for app_id, app in
                            ((a.get("id", c.stem), a) for c, a in apps_citite)
                            if app.get("flatpak"))
    print(f"✔ snap confirmate: {len(toate_snap)}")
    for app_id, nume in toate_snap:
        print(f"   {app_id:18} → snap:{nume}")
    print(f"✔ flatpak confirmate: {len(toate_flatpak)}")
    for app_id, nume in toate_flatpak:
        print(f"   {app_id:18} → flatpak:{nume}")
    if args.dry_run:
        print("(rulează fără --dry-run pentru a scrie în YAML)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
