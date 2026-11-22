#!/usr/bin/env python3
"""Alterna — tabelul de atribuire pentru logo-uri.

Logo-urile sunt resurse ale unor terți (Simple Icons CC0, Wikimedia Commons
cu licențe variabile), deci originea fiecăruia trebuie să fie vizibilă.
Tabelul se **generează din catalog** (`data/apps/*.yaml`) — nu se ține manual:
altfel, o rulare a instrumentului de descărcare ștergea rândurile altora.

Sursa fiecărui logo e cea citată în lista `sources` a aplicației (pagina de
fișier de pe Commons, adăugată automat de `tools/fetch_logos.py`).

Utilizare:
    python tools/build_logos_attribution.py
"""

from __future__ import annotations

import json
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
IESIRI = ROOT / "data" / "logos"
CACHE = Path.home() / ".cache" / "alterna" / "atribuiri-logos.json"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}


def cere_json(url: str) -> dict | None:
    try:
        cerere = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(cerere, timeout=25) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def commons(atribuiri: dict, sursa: str) -> tuple[str, str, str]:
    """(fișier, autor, licență) pentru un logo din Wikimedia Commons."""
    if "commons.wikimedia.org" not in sursa:
        return ("", "", "")
    cheie = sursa
    if cheie not in atribuiri:
        titlu = sursa.split("File:")[-1].split("#")[0]
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&prop=imageinfo&iiprop=extmetadata&titles=File:"
               + urllib.parse.quote(titlu.replace(" ", "_")))
        date = cere_json(url) or {}
        pagini = (date.get("query") or {}).get("pages") or {}
        info: dict = {}
        for valoare in pagini.values():
            info = (valoare.get("imageinfo") or [{}])[0].get("extmetadata") or {}
            break
        autor = re.sub(r"<[^>]+>", "",
                       (info.get("Artist") or {}).get("value", "")).strip()
        licenta = (info.get("LicenseShortName") or {}).get("value", "")
        atribuiri[cheie] = (autor, licenta)
    autor, licenta = atribuiri[cheie]
    return (sursa.split("File:")[-1].split("#")[0], autor, licenta)

def main() -> int:
    yaml = YAML()
    yaml.preserve_quotes = True

    atribuiri: dict = {}
    if CACHE.exists():
        try:
            atribuiri = json.loads(CACHE.read_text(encoding="utf-8"))
        except ValueError:
            atribuiri = {}

    commons_rows: list[tuple[str, str, str, str]] = []
    simple_rows: list[tuple[str, str]] = []
    externe_rows: list[tuple[str, str, str]] = []

    # proveniența logo-urilor venite de pe site-ul oficial / snap / Flathub
    # (scrisă de `tools/fetch_logos.py` în ATRIBUIRE.json)
    fișier_atribuire = IESIRI / "ATRIBUIRE.json"
    proveniență: dict = {}
    if fișier_atribuire.exists():
        try:
            proveniență = json.loads(fișier_atribuire.read_text(encoding="utf-8"))
        except ValueError:
            proveniență = {}

    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        if not app.get("logo"):
            continue
        surse = [str(s) for s in (app.get("sources") or [])]
        commons_url = next((s for s in surse if "commons.wikimedia.org" in s), "")
        if commons_url:
            fisier, autor, licenta = commons(atribuiri, commons_url)
            commons_rows.append((app["id"], fisier, autor, licenta))
        elif app["id"] in proveniență:
            info = proveniență[app["id"]]
            externe_rows.append((app["id"], info.get("tip", "site"),
                                 info.get("adresa", "")))
        else:
            simple_rows.append((app["id"], app.get("website") or ""))

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(atribuiri, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    linii = [
        "# Logo-uri și resurse ale unor terți",
        "",
        "Logo-urile din acest director sunt folosite pentru identificarea "
        "vizuală a aplicațiilor. Ele sunt resurse ale unor terți și **nu sunt "
        "acoperite de licența CC BY-SA 4.0 a catalogului**.",
        "",
        "## Proveniență",
        "",
        "Fișierele sunt descărcate de `tools/fetch_logos.py` din:",
        "",
        "- [Simple Icons](https://simpleicons.org/) — pictograme de marcă, "
        "licența CC0 pentru colecția de pictograme;",
        "- [Wikimedia Commons](https://commons.wikimedia.org/) — logo-urile "
        "oficiale ale proiectelor, pentru brandurile absente din Simple Icons.",
        "",
        "Pentru fiecare fișier, consultă pagina sursă de pe Wikimedia Commons "
        "sau pagina brandului pentru licența și atribuirea exactă. Licențele "
        "variază între utilizare permisă pentru identificare și cerințe "
        "suplementare de atribuire. Drepturile de marcă aparțin titularilor "
        "lor și nu sunt transferate prin licențierea proiectului Alterna.",
        "",
        "## Eliminare și înlocuire",
        "",
        "Dacă un logo nu poate fi redistribuit sau utilizat corespunzător, "
        "elimină fișierul și câmpul `logo` din aplicația YAML corespunzătoare. "
        "Aplicația generează automat o pictogramă de rezervă cu inițiale.",
        "",
        "## Recomandare pentru contribuitori",
        "",
        "Înainte de a adăuga un logo nou:",
        "",
        "1. verifică drepturile și licența sursei;",
        "2. preferă o sursă care permite explicit utilizarea în acest context;",
        "3. documentează originea și atribuirea în commit-ul PR;",
        "4. nu copia un logo dintr-o sursă ale cărei condiții nu le înțelegi.",
        "",
        "## Atribuiri",
        "",
        "Tabelul se **generează din catalog** cu "
        "[`tools/build_logos_attribution.py`](../tools/build_logos_attribution.py) "
        "— nu se ține manual.",
        "",
    ]

    if simple_rows:
        linii += ["### Simple Icons (CC0) și logo-uri oficiale de pe site", "",
                  "| Aplicație | Site oficial |", "|---|---|"]
        for app_id, site in simple_rows:
            linii.append(f"| {app_id} | {site or '—'} |")
        linii.append("")

    if externe_rows:
        linii += ["### De pe site-ul oficial, din snap sau din Flathub", "",
                  "| Aplicație | Sursă | Adresă |", "|---|---|---|"]
        for app_id, tip, adresa in externe_rows:
            linii.append(f"| {app_id} | {tip} | {adresa or '—'} |")
        linii.append("")

    if commons_rows:
        linii += ["### Din Wikimedia Commons", "",
                  "| Aplicație | Fișier original | Autor | Licență |",
                  "|---|---|---|---|"]
        for app_id, fisier, autor, licenta in commons_rows:
            linii.append(f"| {app_id} | {fisier} | {autor or '—'} | {licenta or '—'} |")
        linii.append("")

    (IESIRI / "README.md").write_text("\n".join(linii), encoding="utf-8")
    print(f"atribuire logo-uri: {len(commons_rows)} din Commons, "
          f"{len(externe_rows)} de pe site-uri/snap/Flathub, "
          f"{len(simple_rows)} din Simple Icons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())