#!/usr/bin/env python3
"""Alterna — descarcă capturile de ecran ale aplicațiilor (din Wikidata).

Screenshot-urile vin din **Wikidata** (proprietatea P18 = imaginea oficială a
aplicației), de pe Wikimedia Commons. Avantajul e verificabilitatea: sursa
e o entitate cu citare, nu un „found somewhere".

Fiecare imagine e și o resursă a unui terț, deci:
- se salvează în `data/screenshots/` (nu intră în pachetul aplicației — vezi
  `data/logos/README.md` pentru același motiv);
- atribuirea (autor + licență) se scrie în `data/screenshots/README.md`;
- linkul către fișierul original intră în `sources`, deci utilizatorul poate
  verifica sursa din interfață.

Utilizare:
    python tools/fetch_screenshots.py            # descarcă ce lipsește
    python tools/fetch_screenshots.py --limit 20 # doar primele 20 (test)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"
IESIRI = ROOT / "data" / "screenshots"
CACHE = Path.home() / ".cache" / "alterna" / "wikidata.json"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}

#: Lățimea descărcată (Wikimedia scală la cerere). 520 px = lățimea de
#: afișare în pagina de detalii; mai mult ar umfla bundle-ul degeaba.
LATIME = 520


def citește_json(url: str, timeout: int = 30) -> dict | None:
    try:
        cerere = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(cerere, timeout=timeout) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — rețeaua e best-effort
        return None


def descarcă(url: str, destinație: Path, timeout: int = 60) -> bool:
    """Descarcă un fișier; False dacă nu s-a putut."""
    try:
        cerere = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(cerere, timeout=timeout) as răspuns:
            conținut = răspuns.read()
        if len(conținut) < 2000:      # probabil o pagină de eroare
            return False
        destinație.write_bytes(conținut)
        return True
    except Exception:  # noqa: BLE001
        return False


def p18_din_cache(qid: str) -> str:
    """Numele fișierului de pe Commons (P18), din cache-ul local."""
    if not CACHE.exists():
        return ""
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    ent = (cache.get(f"entity:{qid}") or {}).get("claims") or {}
    for claim in ent.get("P18") or []:
        valoare = (claim.get("mainsnak") or {}).get("datavalue") or {}
        nume = valoare.get("value")
        if isinstance(nume, str):
            return nume
    return ""


def qid_din_sursă(app: dict) -> str:
    """QID-ul aplicației, din sursele citate (linkul spre Wikidata)."""
    for url in app.get("sources") or []:
        if "wikidata.org/wiki/" in url:
            return url.rsplit("/", 1)[-1]
    return ""


def atribute(fișier: str) -> tuple[str, str, str]:
    """(autor, licență, url) pentru fișierul de pe Commons."""
    url = ("https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo"
           "&iiprop=extmetadata&format=json&titles="
           + urllib.parse.quote("File:" + fișier))
    date = citește_json(url) or {}
    pagini = (date.get("query") or {}).get("pages") or {}
    for pagină in pagini.values():
        info = ((pagină.get("imageinfo") or [{}])[0]
                .get("extmetadata") or {})
        autor = re.sub(r"<[^>]+>", "",
                       (info.get("Artist") or {}).get("value", "")).strip()
        licență = (info.get("LicenseShortName") or {}).get("value", "")
        return (autor, licență,
                "https://commons.wikimedia.org/wiki/File:"
                + urllib.parse.quote(fișier.replace(" ", "_")))
    return ("", "", "https://commons.wikimedia.org/wiki/File:"
            + urllib.parse.quote(fișier.replace(" ", "_")))


def converteste(png: Path) -> Path | None:
    """Convertește PNG-ul în JPEG (calitate 82) — un PNG de captură e mare.

    Capturile de ecran se comprimă prost în PNG (zgomotul vizual e exact
    ce penalizează formatul). JPEG la calitate 82 e vizual identic pentru
    această folosire și de cinci ori mai mic — contează, fiindcă imaginile
    intră în pachetul aplicației.
    """
    try:
        from PySide6.QtGui import QImage
    except ImportError:
        return None
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
    args = parser.parse_args()

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
        qid = qid_din_sursă(app)
        fisier = p18_din_cache(qid) if qid else ""
        if not fisier:
            fara += 1
            continue
        destinatie = IESIRI / f"{app_id}.png"
        url = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
               + urllib.parse.quote(fisier.replace(" ", "_"))
               + f"?width={LATIME}")
        if not descarcă(url, destinatie):
            fara += 1
            continue
        jpeg = converteste(destinatie)
        cale_relativa = (f"screenshots/{app_id}.jpg" if jpeg
                         else f"screenshots/{app_id}.png")
        autor, licenta, sursa = atribute(fisier)
        app["screenshot"] = cale_relativa
        surse = list(app.get("sources") or [])
        if sursa not in surse:
            surse.append(sursa)
        app["sources"] = surse
        with cale.open("w", encoding="utf-8") as fh:
            yaml.dump(app, fh)
        atribuiri.append((app_id, fisier, autor, licenta))
        descarcate += 1
        print(f"  + {app_id:16} {fisier[:44]}")

    if atribuiri:
        # Tabelul de atribuire se GENEREAZĂ din catalog (nu se ține manual) —
        # altfel, o rulare ștergea rândurile descărcate de altă dată.
        subprocess.run([sys.executable,
                        str(ROOT / "tools" / "build_screenshots_attribution.py")],
                       check=False)

    print(f"OK {descarcate} capturi descarcate, {sarite} deja existente, "
          f"{fara} fara imagine oficiala")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
