#!/usr/bin/env python3
"""Alterna — verifică numele de pachet Ubuntu pentru fiecare aplicație.

Convenția din `data/README.md`: câmpul `package` e necesar **doar** când
numele pachetului diferă de `id`. Pentru celelalte, pachetul se presupune
a fi `id`.

Problema: o presupunere greșită face ca `refresh_indicators.py` să nu găsească
pachetul — și atunci rangul popcon și statutul „în repo Ubuntu" rămân
incomplete, fără niciun semn că ceva nu se potrivește.

Acest instrument verifică presupunerea pentru toate aplicațiile și raportează
aplicațiile unde numele de pachet din Ubuntu diferă de cel presupus.

Sursa de adevăr: packages.ubuntu.com (arhiva Ubuntu Noble) — aceeași sursă
pe care o folosește `refresh_indicators.py`.

Utilizare:
    python tools/check_packages.py            # raport
    python tools/check_packages.py --suggest  # + propuneri de nume noi
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from tools.refresh_indicators import fetch  # noqa: E402  (utilitarul HTTP)

#: Listele APT locale pentru Ubuntu Noble (main + universe).
APT_LISTS = Path("/var/lib/apt/lists")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"

#: Pagina de căutare a pachetelor Ubuntu.
SEARCH_URL = ("https://packages.ubuntu.com/search?keywords={q}"
               "&searchon=names&suite=noble&section=all")


_INDEX: set[str] | None = None


def local_package_index() -> set[str] | None:
    """Setul de pachete din listele APT locale pentru Ubuntu Noble.

    E sursa cea mai rapidă și cea mai autoritativă — listele sunt chiar
    indicele arhivei. Returnează `None` dacă listele nu sunt disponibile
    (de exemplu, într-un container fără `apt update`).
    """
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    fișiere = sorted(APT_LISTS.glob(
        "archive.ubuntu.com_ubuntu_dists_noble_*_binary-amd64_Packages"))
    if not fișiere:
        return None
    pachete: set[str] = set()
    for fișier in fișiere:
        text = fișier.read_text(encoding="utf-8", errors="replace")
        pachete |= set(re.findall(r"^Package: (\S+)$", text, re.M))
    _INDEX = pachete
    return pachete


def package_exists(package: str, timeout: int = 15) -> bool:
    """Există pachetul în arhiva Ubuntu Noble?

    Preferă listele APT locale (rapide, offline, indexul real al arhivei).
    Altfel cade pe `packages.ubuntu.com` — dar verifică **conținutul**
    paginii, nu statusul HTTP: site-ul întoarce 200 și pentru pachete
    inexistente.
    """
    index = local_package_index()
    if index is not None:
        return package in index
    try:
        page = fetch(f"https://packages.ubuntu.com/noble/{package}",
                     timeout=timeout).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError):
        return False
    return f"Package: {package}" in page


def search_packages(query: str, timeout: int = 15) -> list[str]:
    """Pachete din Ubuntu al căror nume conține `query`."""
    try:
        page = fetch(SEARCH_URL.format(q=urllib.parse.quote(query)),
                     timeout=timeout).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError):
        return []
    # linkurile de pachet din pagina de rezultate: <a href="/noble/<pachet>">
    return sorted(set(re.findall(r'href="/noble/([a-z0-9][a-z0-9+.\-]+)"', page)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suggest", action="store_true",
                        help="propune nume de pachet pentru aplicațiile "
                             "care nu se potrivesc")
    args = parser.parse_args()

    applications = sorted(DATA.glob("*.yaml"))
    probleme: list[tuple[str, str, str]] = []
    grese: list[tuple[str, str]] = []
    for path in applications:
        app = yaml.safe_load(path.read_text(encoding="utf-8"))
        app_id = app.get("id", path.stem)
        presupus = app.get("package") or app_id
        exista = package_exists(presupus)
        in_repo = bool((app.get("indicators") or {}).get("in_ubuntu_repos"))
        if in_repo and not exista:
            # Indicator fals: afirma prezenta in repo, dar pachetul nu exista.
            grese.append((app_id, presupus))
        if exista:
            continue
        explicat = "explicit" if app.get("package") else "implicit"
        probleme.append((app_id, presupus, explicat))

    if grese:
        print(f"✗ {len(grese)} aplicații au `in_ubuntu_repos: true`, dar "
              f"pachetul lor nu există în arhiva Ubuntu — indicatorul e fals:")
        for app_id, presupus in grese:
            print(f"  • {app_id:20} -> {presupus}")
        print()

    if not probleme and not grese:
        print(f"✔ toate cele {len(applications)} aplicații au un pachet "
              f"Ubuntu valid")
        return 0

    print(f"⚠ {len(probleme)} din {len(applications)} aplicații au un nume de "
          f"pachet care nu corespunde în arhiva Ubuntu:\n")
    for app_id, presupus, explicat in probleme:
        print(f"  • {app_id:20} presupune „{presupus}” ({explicat})")
        if args.suggest:
            for nume in search_packages(app_id)[:5]:
                if nume != presupus:
                    print(f"      → posibil: „{nume}”")

    print("\nPentru fiecare aplicație care EXISTă în Ubuntu sub alt nume, "
          "adaugă în fișierul ei YAML:\n"
          "    package: numele-real")
    print("Pentru cele care nu sunt în Ubuntu (snaps, pagini externe, "
          "aplicații comerciale), nu e nevoie de nimic — câmpul rămâne "
          "absent, iar `in_ubuntu_repos: false` e corect.")
    if grese:
        return 1
    print("\n(Indicatoarele `in_ubuntu_repos` sunt corecte — nu s-a găsit "
          "niciunul fals.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
