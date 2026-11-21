#!/usr/bin/env python3
"""Alterna — capturi de ecran de pe site-ul oficial al aplicației (og:image).

Wikidata (P18) are imaginea oficială pentru o parte din aplicații, iar
README-ul depozitului pentru altele; pentru restul, site-ul oficial al
aplicației publică imaginea în metadatele OpenGraph (`og:image`) — aceeași
imagine pe care o văd cei care partajează un link.

Regulile rămân cele ale proiectului (sec. 8 — „totul e verificabil”):
- se ia **doar** de pe site-ul oficial (câmpul `website` din YAML) — nu din
  surse terțe;
- imaginea trebuie să fie suficient de mare (≥400×250 px), ca să nu fie un
  logo sau o iconă;
- sursa (adresa imaginii) intră în `sources`, deci utilizatorul poate
  verifica din interfață;
- atribuirea se scrie în `data/screenshots/README.md`.

Nu intră în pachetul aplicației (la fel ca restul capturilor).

Utilizare:
    python tools/fetch_screenshots_og.py            # descarcă ce lipsește
    python tools/fetch_screenshots_og.py --dry-run  # doar raport
    python tools/fetch_screenshots_og.py --limit 20 # doar primele 20
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"
IESIRI = ROOT / "data" / "screenshots"
CACHE = Path.home() / ".cache" / "alterna" / "og"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)",
      "Accept": "text/html,application/xhtml+xml"}
#: Pauză între cereri — polite și nu suprasolicităm site-urile.
PAUZA = 1.5
#: Lățimea capturii salvate (restul e identic cu `fetch_screenshots.py`).
LATIME = 520
#: Dimensiuni minime (aceeași regulă ca la celelalte capturi).
MIN_LATIME = 400
MIN_INALTIME = 250
#: Limita de descărcare a paginii (HTML).
MAX_HTML = 3 * 1024 * 1024

RE_OG = re.compile(
    r"""<meta[^>]+(?:property|name)=["'](?:og:image(?::secure_url)?|twitter:image)"""
    r"""["'][^>]*content=["']([^"']+)["']""", re.IGNORECASE)
#: Captură de ecran găsită direct în pagină (alt sau adresă conține
#: „screenshot”/„captură”) — preferată față de imaginea de prezentare.
RE_IMG = re.compile(r"""<img[^>]+src=["']([^"']+)["'][^>]*>""", re.IGNORECASE)
RE_IMG_ALT = re.compile(r"""<img[^>]+alt=["']([^"']*)["'][^>]*>""",
                       re.IGNORECASE)
CUVINTE_CAPTURA = re.compile(r"(screenshot|screen[-_ ]?shot|captur[ăa])",
                             re.IGNORECASE)

RE_OG_ALT = re.compile(
    r"""<meta[^>]+content=["']([^"']+)["'][^>]*"""
    r"""(?:property|name)=["'](?:og:image(?::secure_url)?|twitter:image)["']""",
    re.IGNORECASE)
#: Adrese care NU sunt capturi (logo-uri, badge-uri, pictograme).
NU_E_CAPTURA = re.compile(
    r"(logo|icon|favicon|badge|avatar|spacer|blank|1x1|pixel|emoji|"
    r"apple-touch|og-default|social)", re.IGNORECASE)


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
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
    except ImportError:
        return None
    qapp()
    imagine = QImage(str(png))
    if imagine.isNull():
        return None
    # Redimensionare: capturile de prezentare (og:image) vin adesea la
    # 1600–2000 px lățime și ar umfla pachetul aplicației.
    if imagine.width() > LATIME:
        imagine = imagine.scaledToWidth(LATIME, Qt.SmoothTransformation)
    jpeg = png.with_suffix(".jpg")
    if not imagine.save(str(jpeg), "JPEG", 82):
        return None
    png.unlink()
    return jpeg


def url_sigur(url: str) -> str:
    """Adresă URL cu caracterele non-ASCII codificate (altfel urllib pica).

    Unele site-uri trimit adrese de imagine cu caractere Unicode (ex.:
    „â”) — `urllib` le-ar refuza cu UnicodeEncodeError, oprind uneltele.
    """
    parti = urllib.parse.urlsplit(url)
    cale = urllib.parse.quote(parti.path, safe="/%:@!$&'()*+,;=~-._")
    interogare = urllib.parse.quote(parti.query, safe="=&;:@!$'()*+,/?%-._~")
    return urllib.parse.urlunsplit((parti.scheme, parti.netloc, cale,
                                    interogare, parti.fragment))


def citește_pagină(url: str, timeout: int = 25) -> str:
    """Descarcă HTML-ul paginii (din cache, dacă există)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cheie = CACHE / (urllib.parse.quote(url, safe="") + ".html")
    if cheie.exists() and cheie.stat().st_size:
        return cheie.read_text(encoding="utf-8", errors="replace")
    try:
        cerere = urllib.request.Request(url_sigur(url), headers=UA)
        with urllib.request.urlopen(cerere, timeout=timeout) as răspuns:
            date = răspuns.read(MAX_HTML + 1)
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeEncodeError,
            ValueError):
        return ""
    if len(date) > MAX_HTML:
        date = date[:MAX_HTML]
    html = date.decode("utf-8", errors="replace")
    cheie.write_text(html, encoding="utf-8")
    return html


def captura_din_pagină(html: str, url_pagina: str) -> str:
    """Prima imagine din pagină care pare o captură de ecran (alt/src)."""
    for potrivire in RE_IMG.finditer(html):
        eticheta = potrivire.group(0)
        if not CUVINTE_CAPTURA.search(eticheta):
            continue
        adresa = potrivire.group(1).strip()
        if not adresa or NU_E_CAPTURA.search(adresa):
            continue
        return urllib.parse.urljoin(url_pagina, adresa)
    return ""


def imagine_din_html(html: str, url_pagina: str) -> str:
    """Adresa imaginii OpenGraph din pagină (absolută), sau „”."""
    for model in (RE_OG, RE_OG_ALT):
        potrivire = model.search(html)
        if not potrivire:
            continue
        adresa = potrivire.group(1).strip()
        if not adresa or NU_E_CAPTURA.search(adresa):
            continue
        return urllib.parse.urljoin(url_pagina, adresa)
    return ""


def descarcă(url: str, destinație: Path, timeout: int = 45) -> bool:
    try:
        cerere = urllib.request.Request(url_sigur(url), headers=UA)
        with urllib.request.urlopen(cerere, timeout=timeout) as răspuns:
            date = răspuns.read()
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeEncodeError,
            ValueError):
        return False
    if not date:
        return False
    destinație.write_bytes(date)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=0,
                        help="maximum de aplicații procesate (0 = toate)")
    parser.add_argument("--forță", action="store_true",
                        help="redescarcă și ce există deja")
    parser.add_argument("--dry-run", action="store_true",
                        help="nu scrie nimic, doar raportează")
    args = parser.parse_args()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    IESIRI.mkdir(parents=True, exist_ok=True)
    descarcate, sarite, fara = 0, 0, 0
    tabel: list[tuple[str, str, str]] = []

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

        site = (app.get("website") or "").strip()
        if not site.startswith("http"):
            fara += 1
            continue

        html = citește_pagină(site)
        url_imagine = ""
        if html:
            # preferă o captură de ecran reală; altfel, imaginea oficială
            # de prezentare (og:image)
            url_imagine = captura_din_pagină(html, site) or imagine_din_html(
                html, site)
        if not url_imagine:
            fara += 1
            continue

        if args.dry_run:
            print(f"  ? {app_id:16} {url_imagine[:64]}")
            descarcate += 1
            time.sleep(PAUZA)
            continue

        brut = IESIRI / f"{app_id}.img"
        if not descarcă(url_imagine, brut):
            fara += 1
            continue
        latime, inaltime = dimensiuni(brut)
        if latime < MIN_LATIME or inaltime < MIN_INALTIME:
            brut.unlink(missing_ok=True)
            fara += 1
            continue

        png = IESIRI / f"{app_id}.png"
        brut.rename(png)
        jpeg = converteste_jpeg(png)
        cale_relativa = (f"screenshots/{app_id}.jpg" if jpeg
                         else f"screenshots/{app_id}.png")

        app["screenshot"] = cale_relativa
        surse = list(app.get("sources") or [])
        if url_imagine not in surse:
            surse.append(url_imagine)
        app["sources"] = surse
        with cale.open("w", encoding="utf-8") as fh:
            yaml.dump(app, fh)
        tabel.append((app_id, site, url_imagine))
        descarcate += 1
        print(f"  + {app_id:16} {url_imagine[:64]}")
        time.sleep(PAUZA)

    if tabel:
        cu = IESIRI / "README.md"
        linii = (cu.read_text(encoding="utf-8").splitlines() if cu.exists()
                 else ["# Capturi de ecran", ""])
        titlu = "## De pe site-ul oficial al aplicației"
        if titlu in linii:
            linii = linii[:linii.index(titlu)]
        linii.append("")
        linii.append(titlu)
        linii.append("")
        linii.append("Descărcate de "
                     "[`tools/fetch_screenshots_og.py`](../tools/fetch_screenshots_og.py) "
                     "din imaginea oficială de prezentare (metadatele OpenGraph) "
                     "a site-ului oficial al aplicației.")
        linii.append("")
        linii.append("| Aplicație | Site oficial | Imagine |")
        linii.append("|---|---|---|")
        for app_id, site, url_imagine in tabel:
            linii.append(f"| {app_id} | {site} | {url_imagine} |")
        cu.write_text("\n".join(linii) + "\n", encoding="utf-8")

    print(f"OK {descarcate} capturi descarcate, {sarite} deja existente, "
          f"{fara} fara imagine oficiala")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
