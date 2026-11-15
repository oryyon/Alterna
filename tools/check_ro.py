#!/usr/bin/env python3
"""Alterna — verifica suportul pentru limba romana din surse publice.

Punctul 8 din review ("verifica cele 100 de aplicatii, in special limba
romana"): valoarea `details.romanian_language` trebuie sa fie o **verificare**,
nu o estimare.

Trei surse automate, toate fara chei API:

1. **Indexul `Contents` al arhivei Ubuntu** — listeaza fiecare fisier din
   arhiva si pachetul care il contine. Daca exista
   `usr/share/locale/ro/LC_MESSAGES/<aplicatie>.mo`, interfata **este**
   tradusa in romana.
2. **Fisierul de traducere din repository** (`po/ro.po` si asemenea).
3. **Arborele repository-ului** (API GitHub `git/trees`), o cerere per app.

Criteriul de acceptare e strict, ca sa nu se confunde aplicatii cu nume
asemanatoare: fisierul `.mo` trebuie sa poarte numele aplicatiei (eventual cu
sufix numeric: `gimp20.mo`), iar pachetul care il contine trebuie sa fie
inrudit cu aplicatia (`krita-l10n`, `gimp-data`, `kate5-data`). Astfel
`chromium-bsu.mo` (alta aplicatie) si `obsession-logout.mo` nu trec drept
traduceri pentru Chromium, respectiv OBS.

Aplicatiile fara rezultat automat **raman estimate**: absenta dovezilor nu
dovedeste ca nu exista traducere (Mozilla tine traducerile in hg, Chromium in
`chrome/app/i18n/`, Electron in `i18n/`).

Utilizare:
    python tools/check_ro.py            # raport
    python tools/check_ro.py --apply    # marcheaza confirmarile in YAML
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

APT_LISTS = Path("/var/lib/apt/lists")
DISTRO = "noble"

#: Indexul `Contents` al arhivei: fisier -> pachet. Singura sursa cuprinsa.
CONTENTS_URL = f"http://archive.ubuntu.com/ubuntu/dists/{DISTRO}/Contents-amd64.gz"

#: Cache local cu liniile de interes (doar traducerile romaneesti).
CACHE = Path.home() / ".cache" / "alterna" / "contents-ro.txt"

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Alterna-i18n-check/0.2"}

#: Conventiile de fisier de traducere din repository, in ordinea probabilitatii.
CANDIDATE_REPO = (
    "po/ro.po",
    "translations/ro.po",
    "translations/ro/ro.po",
    "po/ro/ro.po",
    "locale/ro.po",
    "po-ro.po",
    "i18n/ro.json",
    "src/po/ro.po",
)

#: Repository-uri care nu sunt pe GitHub, dar au oglinda acolo.
OGLINDIRI = {
    "https://invent.kde.org/utilities/kate": "KDE/kate",
    "https://invent.kde.org/multimedia/kdenlive": "KDE/kdenlive",
    "https://invent.kde.org/graphics/krita": "KDE/krita",
}

#: Cai de traducere romanesti specifice unei aplicatii, gasite in arborele
#: repository-ului. Sunt pastrate aici ca dovada sa nu depinda de limita de
#: 60 de cereri/ora a API-ului GitHub.
CAI_SPECIFICE: dict[str, tuple[str, ...]] = {
    "blender": ("locale/po/ro.po",),
    "joplin": ("packages/app-desktop/locales/ro.json",),
    "lmms": ("data/locale/ro.ts",),
    "penpot": ("frontend/translations/ro.po",),
    "vokoscreenng": ("src/language/ro.ts",),
}

#: Aplicatii excluse din verificarea automata: numele coincide, dar obiectul
#: e altul. Fara aceasta lista, dovezile ar fi inselatoare.
EXCLUDERI = {
    "kazam": ("pachetul Ubuntu `kazam` este un recorder de webcam; aplicația "
              "din catalog este recorderul de ecran (KDE)"),
}

#: Fisierele de traducere romana din arborele repository-ului.
RE_ARBORE = re.compile(
    r"(^|/)(ro|ro_[A-Za-z]+)\.(po|json|ts|xml|properties|mo)$"
    r"|(^|/)ro/.*\.(po|json|ts|xml|properties)$"
    r"|[_-]ro\.(po|json|ts|xml|properties)$",
    re.IGNORECASE)

#: Directoare cu fisiere de exemplu sau documentatie: nu sunt traducerea
#: interfetei, chiar daca se numesc `ro`.
EXCLUSE = ("/doc/", "/docs/", "/example", "/sample", "/test/", "/demo/")


# --------------------------------------------------------------------------
# Indexul arhivei Ubuntu: pachet -> componenta + dependente
# --------------------------------------------------------------------------
def citeste_index() -> dict[str, tuple[str, list[str]]]:
    """Intoarce {pachet: (componenta, dependente)} din listele APT locale."""
    index: dict[str, tuple[str, list[str]]] = {}
    fisiere = sorted(APT_LISTS.glob(
        "archive.ubuntu.com_ubuntu_dists_noble_*_binary-amd64_Packages"))
    for fisier in fisiere:
        m = re.search(r"noble_([a-z0-9-]+)_binary", fisier.name)
        componenta = m.group(1) if m else "main"
        pachet: str | None = None
        dependente: list[str] = []
        for linie in fisier.read_text(encoding="utf-8", errors="replace").splitlines():
            if linie.startswith("Package: "):
                if pachet:
                    index.setdefault(pachet, (componenta, dependente))
                pachet = linie.split(": ", 1)[1].strip()
                dependente = []
            elif pachet and linie.startswith(("Depends: ", "Recommends: ")):
                for grup in linie.split(": ", 1)[1].split(","):
                    prima = grup.split("|")[0].strip()
                    dependente.append(prima.split()[0] if prima else "")
        if pachet:
            index.setdefault(pachet, (componenta, dependente))
    return index


# --------------------------------------------------------------------------
# Sursa 1: indexul `Contents` al arhivei
# --------------------------------------------------------------------------
def extrage_ro(flux) -> dict[str, set[str]]:
    """Din indexul `Contents`, extrage {nume .mo -> pachete care il contin}.

    Formatul liniei: `cale/fisier<tab>componenta/pachet`.
    """
    mo: dict[str, set[str]] = {}
    for linie in flux:
        if "locale/ro/" not in linie:
            continue
        parti = linie.rsplit(None, 1)
        if len(parti) != 2:
            continue
        cale, pachet = parti
        if not cale.endswith(".mo"):
            continue
        nume = cale.rsplit("/", 1)[-1][: -len(".mo")]
        mo.setdefault(nume, set()).add(pachet.split("/")[-1])
    return mo


def ro_locale(force: bool = False) -> dict[str, set[str]]:
    """Traducerile romaneesti din arhiva, din cache sau descarcand indexul."""
    if CACHE.exists() and not force:
        with CACHE.open(encoding="utf-8", errors="replace") as fh:
            return extrage_ro(fh)
    print("  descarcare index Contents (aproximativ 50 MB)...", file=sys.stderr)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    cerere = urllib.request.Request(CONTENTS_URL, headers=UA)
    with urllib.request.urlopen(cerere, timeout=300) as raspuns:
        with gzip.GzipFile(fileobj=raspuns) as gz:
            text = io.TextIOWrapper(gz, encoding="utf-8", errors="replace")
            for linie in text:
                if "locale/ro/" in linie:
                    with CACHE.open("a", encoding="utf-8") as fh:
                        fh.write(linie)
    with CACHE.open(encoding="utf-8", errors="replace") as fh:
        return extrage_ro(fh)


def nume_inrudit(nume: str, baza: str) -> bool:
    """True daca `nume` e numele aplicatiei sau un derivat al lui.

    Recunoaste formele reale din arhiva: `krita` -> `krita-l10n`,
    `gimp` -> `gimp-data`, `kate` -> `kate5-data`. Exclude `libgimp2.0t64`,
    care incepe cu alt prefix.
    """
    if not baza:
        return False
    if nume == baza:
        return True
    if not nume.startswith(baza):
        return False
    rest = nume[len(baza):]
    return rest[0].isdigit() or rest[0] in "-+._"


def mo_al_aplicatiei(baze: set[str], mo: dict[str, set[str]]) -> tuple[bool, str]:
    """Cauta un `.mo` al aplicatiei, livrat de un pachet inrudit cu ea."""
    baza = sorted(baze, key=len, reverse=True)[0]
    for nume_mo, pachete in mo.items():
        mic = nume_mo.lower()
        if not any(re.fullmatch(rf"{re.escape(b)}(\d+)?", mic) for b in baze):
            continue
        comune = sorted(p for p in pachete if nume_inrudit(p, baza))
        if comune:
            return True, (f"{comune[0]}: "
                          f"usr/share/locale/ro/LC_MESSAGES/{nume_mo}.mo")
    return False, ""


# --------------------------------------------------------------------------
# Sursa 2 si 3: repository-ul aplicatiei
# --------------------------------------------------------------------------
def repo_github(app: dict) -> str:
    """Repository-ul GitHub al aplicatiei, sau sirul gol."""
    url = (app.get("indicators") or {}).get("stars_url") or ""
    if not url:
        return ""
    if url.startswith("https://github.com/"):
        return url[len("https://github.com/"):].strip("/")
    return OGLINDIRI.get(url.rstrip("/"), "")


def are_traducere(repo: str, timeout: int = 6,
                  extra: tuple[str, ...] = ()) -> str:
    """Calea fisierului de traducere gasit in repository, sau sirul gol."""
    if not repo:
        return ""

    cai = tuple(extra) + CANDIDATE_REPO

    def probe(cale: str) -> str:
        url = f"https://raw.githubusercontent.com/{repo}/HEAD/{cale}"
        try:
            request = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(request, timeout=timeout) as raspuns:
                if raspuns.status == 200 and len(raspuns.read()) > 200:
                    return cale
        except (urllib.error.URLError, OSError):
            pass
        return ""

    with ThreadPoolExecutor(max_workers=len(cai)) as bazin:
        rezultate = list(bazin.map(probe, cai))
    for cale, gasit in zip(cai, rezultate):
        if gasit:
            return gasit
    return ""


def traducere_in_arbore(repo: str, timeout: int = 12) -> str:
    """Cauta fisiere de traducere romana in arborele repository-ului.

    Foloseste API-ul GitHub (`git/trees`), o singura cerere per repository.
    Limitarea fara token: 60 de cereri pe ora.
    """
    if not repo:
        return ""
    cache = Path.home() / ".cache" / "alterna" / "arbori" / (repo + ".txt")
    if cache.exists():
        for linie in cache.read_text(encoding="utf-8", errors="replace").splitlines():
            if RE_ARBORE.search(linie) and not any(
                    e in linie.lower() for e in EXCLUSE):
                return linie
        return ""
    url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": UA["User-Agent"], "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=timeout) as raspuns:
            date = json.loads(raspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return ""
    if date.get("truncated"):
        # arborele e prea mare: cautarea nu e exhaustiva -> nu dovedeste nimic
        return ""
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8") as fh:
        for intrare in date.get("tree", []):
            if intrare.get("type") == "blob":
                fh.write(intrare.get("path", "") + "\n")
    for intrare in date.get("tree", []):
        cale = intrare.get("path", "")
        if intrare.get("type") != "blob" or not RE_ARBORE.search(cale):
            continue
        if any(excl in cale.lower() for excl in EXCLUSE):
            continue
        return cale
    return ""


# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="marcheaza confirmarile in YAML (confidence: manual)")
    args = parser.parse_args()

    index = citeste_index()
    mo = ro_locale()
    print(f"OK index Ubuntu: {len(index)} pachete, "
          f"{len(mo)} traduceri romaneesti in arhiva")

    yaml_rw = YAML()
    yaml_rw.preserve_quotes = True
    yaml_rw.width = 4096

    confirmate: list[tuple[str, str]] = []
    neconfirmate: list[str] = []
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml_rw.load(cale.read_text(encoding="utf-8"))
        app_id = app.get("id", cale.stem)
        nume_app = app.get("name") or app_id
        baze = {app_id.lower(), nume_app.split()[0].lower()} - {""}

        if app_id in EXCLUDERI:
            print(f"  x {app_id:18} exclus: {EXCLUDERI[app_id]}")
            continue

        dovedire = ""
        are, dov = mo_al_aplicatiei(baze, mo)
        if are:
            dovedire = dov
        if not dovedire:
            repo = repo_github(app)
            gasit = are_traducere(repo, extra=CAI_SPECIFICE.get(app_id, ()))
            if gasit:
                dovedire = f"{repo}/{gasit}"
            else:
                gasit = traducere_in_arbore(repo)
                if gasit:
                    dovedire = f"{repo}/{gasit}"

        if dovedire:
            confirmate.append((app_id, dovedire))
            print(f"  + {app_id:18} {dovedire}")
            if not args.apply:
                continue
            det = app.setdefault("details", {})
            if not det.get("romanian_language"):
                # Dovezirea contrazice catalogul: fisierul de traducere exista,
                # deci interfata e traducata. Valoarea se corecteaza.
                print(f"      ! corectie: catalogul spunea 'fara romana', "
                      f"dar {dovedire} exista")
                det["romanian_language"] = True
            app.setdefault("confidence", {})["details.romanian_language"] = "manual"
            with cale.open("w", encoding="utf-8") as fh:
                yaml_rw.dump(app, fh)
        else:
            neconfirmate.append(app_id)
            print(f"  . {app_id:18} nerezolvat automat")

    print(f"\nOK {len(confirmate)} confirmari, {len(neconfirmate)} raman de verificat manual")
    if neconfirmate:
        print("  " + ", ".join(neconfirmate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
