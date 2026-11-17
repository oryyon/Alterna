#!/usr/bin/env python3
"""Alterna — importă aplicații noi în catalog, cu date verificabile.

Extinderea catalogului nu înseamnă „copiat descrieri de pe web”: fiecare
applicație nouă are **descrierea, categoria, alternativele și etichetele**
curate editorial (fișierul de semințe), iar **datele obiective se iau din
Wikidata** — anul primei versiuni, site-ul oficial, dezvoltatorul, licența —
fiecare cu sursa citată în `sources`.

Regulă: ce nu poate fi verificat **nu se inventează**. Dacă Wikidata nu
găsește aplicația, importul e oprit pentru ea și raportat, ca omul să verifice
— nu se scrie o intrare fără surse.

Pipeline (după import):
    python tools/refresh_indicators.py    # popcon, stele, versiuni, repo
    python tools/refresh_sizes.py         # dimensiunea, măsurată din arhivă
    python tools/check_packages.py        # numele de pachet
    python tools/fetch_logos.py           # logo-urile
    python tools/check_ro.py              # limba română
    python tools/check_installed_sources.py  # snap / Flatpak

Utilizare:
    python tools/import_apps.py --dry-run   # doar raportul
    python tools/import_apps.py             # scrie data/apps/<id>.yaml
"""

from __future__ import annotations

import argparse
import json
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
SEMINTE = ROOT / "tools" / "seminte"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}

#: Cache local (Wikidata se interoghează rar; etichetele se rezolvă în bloc).
CACHE = Path.home() / ".cache" / "alterna" / "wikidata.json"

#: Proprietăți Wikidata folosite.
P_INSTANTA = "P31"        # instance of
P_DEVELOPER = "P178"      # developer
P_LICENTA = "P277"        # license
P_PLATFORM = "P400"       # platform
P_START = "P571"          # inception
P_SITE = "P856"           # official website
P_REPO = "P1324"          # source code repository

#: Etichete de licență care înseamnă software liber.
LIBERE = (
    "gpl", "lgpl", "agpl", "mit", "apache", "bsd", "mpl", "epl", "cddl",
    "zlib", "artistic", "unlicense", "cc0", "python", "ruby", "openssl",
    "isc", "gfdl", "osl", "ms-pl", "eupl", "qpl", "ipl", "wtfpl",
    "postgresql", "vim", "ncurses", "curl", "boost",
    # etichetele lungi din Wikidata („GNU General Public License v2.0”)
    "general public license", "mozilla public license", "eclipse public license",
    "common development and distribution license", "open software license",
)

#: Etichete de licență care înseamnă software proprietar.
PROPRIETARE = ("proprietar", "freeware", "shareware", "commercial",
               "closed source")


def citește_json(url: str, timeout: int = 25) -> dict | None:
    """GET JSON; None la orice eșec (rețeaua e best-effort, nu blocantă)."""
    try:
        cerere = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(cerere, timeout=timeout) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


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


def caută_qid(nume: str, cache: dict) -> str | None:
    """Caută entitatea Wikidata pentru un nume de aplicație."""
    cheie = f"search:{nume.lower()}"
    if cheie in cache:
        return cache[cheie] or None
    url = ("https://www.wikidata.org/w/api.php?action=wbsearchentities"
           f"&search={urllib.parse.quote(nume)}&language=en&format=json&limit=8")
    date = citește_json(url)
    rezultate = (date or {}).get("search") or []
    ales = None
    for hit in rezultate:
        eticheta = (hit.get("label") or "").lower()
        descriere = (hit.get("description") or "").lower()
        # vrem aplicația software cu numele exact (nu un film, nu un joc)
        if eticheta == nume.lower() and any(
                cuvânt in descriere
                for cuvânt in ("software", "application", "program", "editor",
                               "player", "suite", "desktop", "manager",
                               "tool", "platform")):
            ales = hit["id"]
            break
    cache[cheie] = ales or ""
    return ales



def entitate(qid: str, cache: dict) -> dict | None:
    """Datele complete ale unei entități Wikidata."""
    cheie = f"entity:{qid}"
    if cheie in cache:
        return cache[cheie] or None
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    date = citește_json(url)
    entități = (date or {}).get("entities") or {}
    ent = entități.get(qid)
    cache[cheie] = ent or {}
    return ent


def rezolva_etichete(qids: set[str], cache: dict) -> dict[str, str]:
    """Etichetele (în română sau engleză) pentru o mulțime de QID-uri."""
    lipsă = sorted(q for q in qids if q and f"label:{q}" not in cache)
    if lipsă:
        for start in range(0, len(lipsă), 50):
            grup = lipsă[start:start + 50]
            url = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
                   f"&ids={'|'.join(grup)}&props=labels"
                   "&languages=ro|en&format=json")
            date = citește_json(url) or {}
            for qid, ent in (date.get("entities") or {}).items():
                etichete = ent.get("labels") or {}
                valoare = (etichete.get("ro")
                           or etichete.get("en") or {}).get("value")
                cache[f"label:{qid}"] = valoare or ""
    return {qid: cache.get(f"label:{qid}") or qid for qid in qids}


def valoare_simplă(claim: dict) -> object | None:
    """Valoarea „simplă” a unei afirmații Wikidata (ignoră calificările)."""
    snaks = claim.get("mainsnak") or {}
    if snaks.get("snaktype") != "value":
        return None
    valoare = (snaks.get("datavalue") or {}).get("value")
    if isinstance(valoare, dict) and "id" in valoare:
        return valoare["id"]
    if isinstance(valoare, dict) and "time" in valoare:
        return valoare["time"]
    return valoare


def primul(ent: dict, proprietate: str) -> object | None:
    """Prima valoare a unei proprietăți."""
    for claim in (ent.get("claims") or {}).get(proprietate) or []:
        valoare = valoare_simplă(claim)
        if valoare is not None:
            return valoare
    return None


def toate_qid(ent: dict, proprietate: str) -> list[str]:
    """Toate valorile QID ale unei proprietăți."""
    qiduri = []
    for claim in (ent.get("claims") or {}).get(proprietate) or []:
        valoare = valoare_simplă(claim)
        if isinstance(valoare, str):
            qiduri.append(valoare)
    return qiduri


def an_din_timp(timp: str | None) -> int | None:
    """Anul din valoarea temporală Wikidata („+2005-06-21T00:00:00Z”)."""
    if not timp:
        return None
    m = re.match(r"^[+-](\d{4})", str(timp))
    return int(m.group(1)) if m else None


def tip_licență(etichetă: str) -> str | None:
    """Traduce eticheta unei licențe în enum-ul proiectului."""
    jos = etichetă.lower()
    if any(cuvânt in jos for cuvânt in LIBERE):
        return "foss"
    if any(cuvânt in jos for cuvânt in PROPRIETARE):
        return "commercial"
    return None


#: Platforme Wikidata → enum-ul proiectului.
PLATFORM_URI = {
    "Q9135": "linux", "Q1066": "windows", "Q170656": "macos",
    "Q94": "android", "Q269480": "web",
}


def platforme_din_wikidata(qids: list[str]) -> list[str]:
    """Platformele recunoscute din Wikidata."""
    return [PLATFORM_URI[q] for q in qids if q in PLATFORM_URI]



def construiește_app(seed: dict, ent: dict, etichete: dict) -> dict:
    """Construiește intrarea de catalog din semință + datele Wikidata."""
    app: dict = {}
    app["id"] = seed["id"]
    app["popularity"] = int(seed.get("popularity", 0))
    app["name"] = seed["name"]
    app["description"] = seed["description"]
    app["category"] = seed["category"]

    # --- licența: preferăm Wikidata (verificabil), altfel semința -----------
    qid_licență = primul(ent, P_LICENTA) if ent else None
    etichetă_licență = etichete.get(qid_licență, "") if qid_licență else ""
    din_wikidata = tip_licență(etichetă_licență)
    app["license"] = seed.get("license") or din_wikidata or "foss"

    app["price"] = seed.get("price", "free")
    app["developer"] = (seed.get("developer")
                        or etichete.get(primul(ent, P_DEVELOPER) or "", ""))
    app["website"] = (seed.get("website")
                       or (primul(ent, P_SITE) if ent else None) or "")

    # --- platforme: semința are prioritate, Wikidata completează ------------
    platforme = list(seed.get("platforms") or [])
    if ent:
        for platformă in platforme_din_wikidata(toate_qid(ent, P_PLATFORM)):
            if platformă not in platforme:
                platforme.append(platformă)
    app["platforms"] = platforme or ["linux"]

    if seed.get("package"):
        app["package"] = seed["package"]
    app["tags"] = list(seed.get("tags") or [])
    app["alternatives"] = list(seed.get("alternatives") or [])
    if seed.get("editors_choice"):
        app["editors_choice"] = True

    detalii: dict = {}
    detalii["install_size_mb"] = int(seed.get("install_size_mb", 0))
    an = an_din_timp(primul(ent, P_START) if ent else None)
    detalii["first_release_year"] = an or seed.get("first_release_year")
    if not an and seed.get("first_release_year"):
        # fără Wikidata, anul vine din semință → rămâne estimare
        detalii["first_release_year"] = seed["first_release_year"]
    detalii["file_formats"] = list(seed.get("file_formats") or [])
    detalii["telemetry"] = seed.get("telemetry", "none")
    detalii["romanian_language"] = bool(seed.get("romanian_language", False))
    app["details"] = detalii

    repo = seed.get("repo") or primul(ent, P_REPO) if ent else None
    if isinstance(repo, str) and not repo.startswith("https://"):
        # sursele non-HTTPS nu intră în catalog (linkul apare în interfață)
        repo = None
    app["indicators"] = {
        "popcon_rank": None, "stars": None,
        "stars_url": repo if isinstance(repo, str) and repo.startswith("http") else None,
        "latest_release": None, "in_ubuntu_repos": False,
    }

    surse = []
    if app["website"]:
        surse.append(app["website"])
    repo = app["indicators"].get("stars_url")
    if repo and repo not in surse:
        surse.append(repo)
    if ent:
        qid = ent.get("id")
        if qid:
            surse.append(f"https://www.wikidata.org/wiki/{qid}")
    app["sources"] = surse

    certitudine: dict = {}
    if an:
        certitudine["details.first_release_year"] = "auto"
    if din_wikidata:
        certitudine["license"] = "auto"
    if certitudine:
        app["confidence"] = certitudine
    return app



def scrie_yaml(app: dict, cale: Path) -> None:
    """Scrie intrarea în formatul proiectului (comentariu de titlu + YAML)."""
    yaml = YAML()
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True
    yaml.width = 4096
    titlu = f"# {app['name']} — {app['description']}\n"
    with cale.open("w", encoding="utf-8") as fh:
        fh.write(titlu)
        yaml.dump(app, fh)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="doar raportul, nu scrie fișierele")
    parser.add_argument("--semințe", type=Path, default=SEMINTE,
                        help="directorul cu fișierele de semințe (YAML)")
    parser.add_argument("--overwrite", action="store_true",
                        help="rescrie intrările existente (după corectarea datelor)")
    args = parser.parse_args()

    if not args.semințe.is_dir():
        print(f"✗ nu există directorul de semințe: {args.semințe}",
              file=sys.stderr)
        return 1

    cache = încarcă_cache()
    yaml = YAML()
    yaml.allow_duplicate_keys = False
    yaml.preserve_quotes = True

    semințe: list[dict] = []
    for fișier in sorted(args.semințe.glob("*.yaml")):
        date = yaml.load(fișier.read_text(encoding="utf-8")) or []
        for intrare in date:
            semințe.append(intrare)
    print(f"✔ {len(semințe)} aplicații în semințe")

    # 1) entitățile Wikidata (cu cache, ca să nu repetăm cererile)
    entități: dict[str, dict] = {}
    lipsă = []
    for seed in semințe:
        qid = seed.get("wikidata_qid")
        if not qid:
            qid = caută_qid(seed.get("wikidata_nume") or seed["name"], cache)
        ent = entitate(qid, cache) if qid else None
        if not ent:
            lipsă.append(seed)
            continue
        entități[seed["id"]] = ent
        time.sleep(0.1)   # politeness pentru API-ul public

    if lipsă:
        fără_entitate = [s_ for s_ in lipsă if s_.get("website")]
        fără_sursă = [s_ for s_ in lipsă if not s_.get("website")]
        if fără_entitate:
            print(f"⚠ {len(fără_entitate)} aplicații nu au entitate Wikidata — "
                  "se importă doar cu site-ul din semință (restul rămâne estimare):")
            for seed in fără_entitate:
                print(f"    {seed['id']:16} ({seed['name']})")
        if fără_sursă:
            print(f"✗ {len(fără_sursă)} aplicații nu au nici entitate Wikidata, "
                  "nici site — nu se importă:")
            for seed in fără_sursă:
                print(f"    {seed['id']:16} ({seed['name']})")
        lipsă = fără_entitate

    # 2) etichetele necesare (dezvoltator, licență, platformă) — în bloc
    qids: set[str] = set()
    for ent in entități.values():
        for proprietate in (P_DEVELOPER, P_LICENTA, P_PLATFORM):
            qids.update(toate_qid(ent, proprietate))
    etichete = rezolva_etichete(qids, cache)

    # 3) scrierea
    scrise, sărite = 0, 0
    for seed in semințe:
        app_id = seed["id"]
        ținta = DATA / f"{app_id}.yaml"
        if ținta.exists() and not args.overwrite:
            print(f"  · {app_id:16} există deja — sărit")
            sărite += 1
            continue
        ent = entități.get(app_id)
        if not ent and not seed.get("website"):
            continue
        app = construiește_app(seed, ent or {}, etichete)
        if not app["website"]:
            print(f"  ! {app_id:16} fără site oficial — nu se importă")
            continue
        if not args.dry_run:
            scrie_yaml(app, ținta)
        scrise += 1
        print(f"  + {app_id:16} {app['website']:42} "
              f"an={app['details']['first_release_year']} "
              f"lic={app['license']}")

    salvează_cache(cache)
    print(f"\n✔ {scrise} aplicații importate, {sărite} sărite "
          f"(existente), {len(lipsă)} fără sursă Wikidata")
    if args.dry_run:
        print("(rulează fără --dry-run pentru a scrie în data/apps/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
