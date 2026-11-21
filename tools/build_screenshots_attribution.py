#!/usr/bin/env python3
"""Alterna — tabelul de atribuire pentru capturile de ecran.

Capturile sunt resurse ale unor terți (Wikimedia Commons, depozite oficiale,
site-urile aplicațiilor), deci fiecare trebuie să-și declare sursa și
licența. Tabelul se **generează din catalog** (`data/apps/*.yaml`), nu se
ține manual: altfel, o rulare a unui instrument de descărcare ștergea rândurile
altora (51 de aplicații au rămas fără atribuire — prins de test).

Sursele se rezolvă în ordine:
1. **Wikimedia Commons** — autorul și licența vin din API-ul Commons (cu cache);
2. **depozit oficial GitHub** — repo-ul și licența lui, din API (cu cache);
3. **site-ul oficial** — adresa imaginii, așa cum e citată în `sources`.

Utilizare:
    python tools/build_screenshots_attribution.py
"""

from __future__ import annotations

import json
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
CACHE = Path.home() / ".cache" / "alterna" / "atribuiri.json"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}
GH_BLOB = re_github = None


def cere_json(url: str) -> dict | None:
    try:
        cerere = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(cerere, timeout=25) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def surse_captura(app: dict) -> list[str]:
    """Adresele surselor care pot fi imaginea capturii."""
    return [str(s) for s in (app.get("sources") or [])]


def commons(atribuiri: dict, sursa: str) -> tuple[str, str, str]:
    """(fișier, autor, licență) pentru o imagine din Wikimedia Commons."""
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
        info = {}
        for valoare in pagini.values():
            info = (valoare.get("imageinfo") or [{}])[0].get("extmetadata") or {}
            break
        import re as _re

        autor = _re.sub(r"<[^>]+>", "", (info.get("Artist") or {}).get("value", "")).strip()
        licenta = (info.get("LicenseShortName") or {}).get("value", "")
        atribuiri[cheie] = (autor, licenta)
    autor, licenta = atribuiri[cheie]
    return (sursa.split("File:")[-1].split("#")[0], autor, licenta)


def github(atribuiri: dict, sursa: str) -> tuple[str, str]:
    """(depozit, licență) pentru o imagine din README-ul unui repo GitHub."""
    import re as _re

    m = _re.match(r"https://github\.com/([^/]+/[^/]+)/blob/", sursa)
    if not m:
        return ("", "")
    repo = m.group(1)
    cheie = repo.lower()
    if cheie not in atribuiri:
        date = cere_json(f"https://api.github.com/repos/{repo}") or {}
        atribuiri[cheie] = (date.get("license") or {}).get("spdx_id") or ""
    return (repo, atribuiri[cheie])


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
    github_rows: list[tuple[str, str, str, str]] = []
    site_rows: list[tuple[str, str, str]] = []

    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        if not app.get("screenshot"):
            continue
        surse = surse_captura(app)
        commons_url = next((s for s in surse if "commons.wikimedia.org" in s), "")
        github_url = next((s for s in surse if "github.com" in s and "/blob/" in s), "")
        if commons_url:
            fisier, autor, licenta = commons(atribuiri, commons_url)
            commons_rows.append((app["id"], fisier, autor, licenta))
        elif github_url:
            repo, licenta = github(atribuiri, github_url)
            github_rows.append((app["id"], repo, github_url, licenta))
        else:
            imagine = next((s for s in surse
                            if s.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))), "")
            site_rows.append((app["id"], app.get("website") or "", imagine or surse[-1] if surse else ""))

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(atribuiri, ensure_ascii=False, indent=1),
                     encoding="utf-8")

    linii = [
        "# Capturi de ecran",
        "",
        "Imaginile sunt resurse ale unor terți (Wikimedia Commons, depozite "
        "oficiale, site-urile aplicațiilor). Tabelul se **generează din "
        "catalog** cu "
        "[`tools/build_screenshots_attribution.py`](../tools/build_screenshots_attribution.py) "
        "— nu se ține manual.",
        "",
        "Nu fac parte din pachetul aplicației; sunt afișate în aplicație cu "
        "atribuirea sursei (linkul apare în pagina de detalii, la „Surse”).",
        "",
    ]

    if commons_rows:
        linii += ["## Din Wikimedia Commons (proprietatea P18 din Wikidata)", "",
                  "| Aplicație | Fișier original | Autor | Licență |",
                  "|---|---|---|---|"]
        for app_id, fisier, autor, licenta in commons_rows:
            linii.append(f"| {app_id} | {fisier} | {autor or '—'} | {licenta or '—'} |")
        linii.append("")

    if github_rows:
        linii += ["## Din README-ul oficial al proiectului (GitHub)", "",
                  "Descărcate de "
                  "[`tools/fetch_screenshots_github.py`](../tools/fetch_screenshots_github.py) "
                  "din imaginea oficială de prezentare a depozitului.",
                  "",
                  "| Aplicație | Depozit | Imagine | Licență |",
                  "|---|---|---|---|"]
        for app_id, repo, url, licenta in github_rows:
            linii.append(f"| {app_id} | {repo} | {url} | {licenta or '—'} |")
        linii.append("")

    if site_rows:
        linii += ["## De pe site-ul oficial al aplicației", "",
                  "Descărcate de "
                  "[`tools/fetch_screenshots_og.py`](../tools/fetch_screenshots_og.py) "
                  "din imaginea oficială de prezentare (metadatele OpenGraph) "
                  "a site-ului oficial al aplicației.",
                  "",
                  "| Aplicație | Site oficial | Imagine |",
                  "|---|---|---|"]
        for app_id, site, imagine in site_rows:
            linii.append(f"| {app_id} | {site} | {imagine} |")
        linii.append("")

    (IESIRI / "README.md").write_text("\n".join(linii), encoding="utf-8")
    print(f"atribuire: {len(commons_rows)} din Commons, {len(github_rows)} din "
          f"GitHub, {len(site_rows)} de pe site-urile oficiale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
