#!/usr/bin/env python3
"""Alterna — capturi de ecran din README-ul oficial al proiectului (GitHub).

Wikidata (proprietatea P18) are imaginea oficială pentru 84 dintre cele 214
aplicații; pentru celelalte 130 imaginea oficială stă în README-ul depozitului
aplicației. Aceeași regulă ca la `fetch_screenshots.py`:

- fișierul se salvează în `data/screenshots/` (nu intră în pachetul aplicației);
- atribuirea (proiect + licență) se scrie în `data/screenshots/README.md`;
- linkul către imaginea originală intră în `sources`, deci utilizatorul poate
  verifica sursa din interfață.

Sunt folosite doar imagini din README-ul oficial al depozitului indicat în
`indicators.stars_url` — nu din surse terțe.

Utilizare:
    python tools/fetch_screenshots_github.py            # descarcă ce lipsește
    python tools/fetch_screenshots_github.py --dry-run  # doar raport
    python tools/fetch_screenshots_github.py --limit 20 # doar primele 20
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"
IESIRI = ROOT / "data" / "screenshots"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}

#: Lățimea capturii salvate (restul e identic cu `fetch_screenshots.py`).
LATIME = 520
#: Dimensiuni minime — o captură adevărată, nu un badge sau o iconă.
MIN_LATIME = 400
MIN_INALTIME = 250
#: Limita de descărcare (o captură e imagine, nu arhivă).
MAX_OCTETI = 15 * 1024 * 1024

#: Modele de imagini care NU sunt capturi de ecran.
EXCLUDE = re.compile(
    r"(shields\.io|badge|travis|codecov|coveralls|circleci|appveyor|"
    r"logo|icon|avatar|favicon|emoji|patreon|sponsor|button|"
    r"\.(svg|gif|ico)(\?|$))",
    re.IGNORECASE,
)

REPO_URL = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)")


def cere_json(url: str, token: str = "") -> dict | None:
    """GET JSON (cu token opțional pentru limita API-ului GitHub)."""
    antet = dict(UA)
    if token:
        antet["Authorization"] = f"Bearer {token}"
    try:
        cerere = urllib.request.Request(url, headers=antet)
        with urllib.request.urlopen(cerere, timeout=30) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def descarcă(url: str, destinație: Path) -> bool:
    """Descarcă o imagine; întoarce False la orice eroare."""
    try:
        cerere = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(cerere, timeout=60) as răspuns:
            date = răspuns.read(MAX_OCTETI + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    if len(date) > MAX_OCTETI or not date:
        return False
    destinație.write_bytes(date)
    return True


def imagini_din_readme(markdown: str) -> list[str]:
    """URL-urile de imagini din README, în ordinea apariției."""
    urluri: list[str] = []
    modele = [
        re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?[^)]*\)"),
        re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE),
    ]
    for model in modele:
        for potrivire in model.finditer(markdown):
            url = potrivire.group(1).strip()
            if url and url not in urluri:
                urluri.append(url)
    return urluri


def url_absolut(url: str, owner: str, repo: str) -> str:
    """Transformă un URL relativ din README într-un URL absolut descărcabil."""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    url = url.split("#", 1)[0].split("?", 1)[0]
    if url.startswith("//"):
        return "https:" + url
    cale = url.lstrip("./")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{cale}"


_APP = None


def qapp():
    """Instanță QGuiApplication offline — QImage are nevoie de ea (pluginuri)."""
    global _APP
    if _APP is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtGui import QGuiApplication
        _APP = QGuiApplication.instance() or QGuiApplication(["alterna-screenshots"])
    return _APP


def dimensiuni(fișier: Path) -> tuple[int, int]:
    """Dimensiunile imaginii (PySide6 e deja dependență a proiectului)."""
    try:
        from PySide6.QtGui import QImage
    except ImportError:
        return (0, 0)
    qapp()
    imagine = QImage(str(fișier))
    if imagine.isNull():
        return (0, 0)
    return (imagine.width(), imagine.height())


def converteste_jpeg(png: Path) -> Path | None:
    """PNG → JPEG (calitate 82) — capturile se comprimă prost în PNG."""
    try:
        from PySide6.QtGui import QImage
    except ImportError:
        return None
    qapp()
    imagine = QImage(str(png))
    if imagine.isNull():
        return None
    jpeg = png.with_suffix(".jpg")
    if not imagine.save(str(jpeg), "JPEG", 82):
        return None
    png.unlink()
    return jpeg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=0,
                        help="maximum de aplicații procesate (0 = toate)")
    parser.add_argument("--forță", action="store_true",
                        help="redescarcă și ce există deja")
    parser.add_argument("--dry-run", action="store_true",
                        help="nu scrie nimic, doar raportează")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    IESIRI.mkdir(parents=True, exist_ok=True)
    atribuiri: list[tuple[str, str, str, str]] = []
    descarcate, sarite, fara = 0, 0, 0

    for cale in sorted(DATA.glob("*.yaml")):
        if args.limit and descarcate + sarite >= args.limit:
            break
        app = yaml.load(cale.read_text(encoding="utf-8"))
        app_id = app.get("id")
        if not app_id:
            continue
        if app.get("screenshot") and not args.forță:
            sarite += 1
            continue

        sursa_repo = ((app.get("indicators") or {}).get("stars_url") or "")
        potrivire = REPO_URL.match(sursa_repo)
        if not potrivire:
            fara += 1
            continue
        owner, repo = potrivire.group(1), potrivire.group(2)

        readme = cere_json(
            f"https://api.github.com/repos/{owner}/{repo}/readme", token)
        if not readme or not readme.get("content"):
            fara += 1
            continue
        try:
            markdown = base64.b64decode(readme["content"]).decode("utf-8", "replace")
        except (ValueError, TypeError):
            fara += 1
            continue

        candidati = []
        for url in imagini_din_readme(markdown):
            if EXCLUDE.search(url):
                continue
            absolut = url_absolut(url, owner, repo)
            if absolut.startswith("https://"):
                candidati.append((url, absolut))
        if not candidati:
            fara += 1
            continue

        if args.dry_run:
            url_relativ, _ = candidati[0]
            print(f"  ? {app_id:16} {url_relativ[:60]}")
            descarcate += 1
            continue

        brut = IESIRI / f"{app_id}.img"
        ales = None
        for url_relativ, url_abs in candidati[:6]:
            if not descarcă(url_abs, brut):
                continue
            latime, inaltime = dimensiuni(brut)
            if latime < MIN_LATIME or inaltime < MIN_INALTIME:
                # badge, logo sau iconă — nu e captură de ecran
                brut.unlink(missing_ok=True)
                continue
            ales = url_relativ
            break
        if ales is None:
            fara += 1
            continue
        url_relativ = ales

        png = IESIRI / f"{app_id}.png"
        brut.rename(png)
        jpeg = converteste_jpeg(png)
        cale_relativa = (f"screenshots/{app_id}.jpg" if jpeg
                         else f"screenshots/{app_id}.png")

        meta = cere_json(f"https://api.github.com/repos/{owner}/{repo}", token) or {}
        licenta = ((meta.get("license") or {}).get("spdx_id") or "")
        sursa = (f"https://github.com/{owner}/{repo}/blob/HEAD/"
                 + urllib.parse.quote(url_relativ.lstrip("./")))
        app["screenshot"] = cale_relativa
        surse = list(app.get("sources") or [])
        if sursa not in surse:
            surse.append(sursa)
        app["sources"] = surse
        with cale.open("w", encoding="utf-8") as fh:
            yaml.dump(app, fh)
        atribuiri.append((app_id, f"{owner}/{repo}", sursa, licenta))
        descarcate += 1
        print(f"  + {app_id:16} {url_relativ[:44]}")

    if atribuiri:
        cu = IESIRI / "README.md"
        if cu.exists():
            linii = cu.read_text(encoding="utf-8").splitlines()
        else:
            linii = ["# Capturi de ecran", "",
                     "Nu fac parte din pachetul aplicației; sunt afișate în "
                     "aplicație cu atribuirea sursei (linkul apare în pagina de "
                     "detalii, la „Surse”).", "",
                     "| Aplicație | Fișier original | Autor | Licență |",
                     "|---|---|---|---|"]
        linii.append("")
        linii.append("## Din README-ul oficial al proiectului (GitHub)")
        linii.append("")
        linii.append("Descărcate de "
                     "[`tools/fetch_screenshots_github.py`](../tools/fetch_screenshots_github.py) "
                     "din README-ul depozitului oficial al aplicației.")
        linii.append("")
        linii.append("| Aplicație | Depozit | Imagine | Licență |")
        linii.append("|---|---|---|---|")
        for app_id, repo, sursa, licenta in atribuiri:
            linii.append(f"| {app_id} | {repo} | {sursa} | {licenta or '—'} |")
        cu.write_text("\n".join(linii) + "\n", encoding="utf-8")

    print(f"OK {descarcate} capturi descarcate, {sarite} deja existente, "
          f"{fara} fara imagine oficiala")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
