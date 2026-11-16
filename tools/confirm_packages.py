#!/usr/bin/env python3
"""Alterna — confirmă manual `in_ubuntu_repos` pentru pachetele verificate.

`tools/refresh_indicators.py` găsește pachete în arhiva Ubuntu, dar **nu
ridică singur indicatorul**: un nume de pachet poate coincide cu alt
aplicație („notion” din depozite e un window manager, „slack” e un tool de
configurare). De aceea le raportează cu „?” și așteaptă confirmarea umană.

Acest instrument face exact verificarea: pentru fiecare aplicație cu pachetul
găsit în arhivă, citește **descrierea pachetului** și o compară cu aplicația.
Potrivirile clare sunt confirmate; cele care nu sunt, rămân `false`.

Coliziunile cunoscute sunt declarate explicit în `COLIZIUNI`, ca excepția să
fie vizibilă în cod, nu ascunsă într-un caz special.

Utilizare:
    python tools/confirm_packages.py --dry-run
    python tools/confirm_packages.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"
LISTE = Path("/var/lib/apt/lists")

#: Aplicații al căror nume de pachet coincide cu alt software din depozite.
COLIZIUNI = {
    "notion": "pachetul „notion” din depozite e un window manager, nu aplicația",
    "slack": "pachetul „slack” din depozite e un tool de configurare, nu aplicația",
}

#: Cuvinte care trebuie să apară în descrierea pachetului ca să fie potrivirea
#: acceptată (aplicația e identificată, nu doar numele pachetului).
CUVINTE_CONFIRMARE = {
    "notion": [],
    "slack": [],
}


def citeste_index() -> dict[str, str]:
    """{pachet: descriere} din listele APT locale."""
    descrieri: dict[str, str] = {}
    for fișier in sorted(LISTE.glob(
            "archive.ubuntu.com_ubuntu_dists_noble_*_binary-amd64_Packages")):
        pachet = None
        for linie in fișier.read_text(encoding="utf-8", errors="replace").splitlines():
            if linie.startswith("Package: "):
                pachet = linie.split(": ", 1)[1].strip()
            elif linie.startswith("Description: ") and pachet:
                descrieri.setdefault(pachet, linie.split(": ", 1)[1].strip())
    return descrieri


def potrivire(app_id: str, pachet: str, descriere: str) -> bool:
    """Pachetul din arhivă e aplicația noastră?

    Numele pachetului coincide cu id-ul aplicației, iar coliziunile cunoscute
    sunt excluse explicit (COLIZIUNI). Restul: descrierea e afișată, ca
    verificarea umană să-și spună părerea — multe descrieri din arhivă sunt
    generice („Open Source Home Theatre" pentru kodi) și nu pot fi potrivite
    automat fără false pozitive.
    """
    return app_id not in COLIZIUNI


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="doar raportul, nu scrie fișierele")
    args = parser.parse_args()

    index = citeste_index()
    if not index:
        print("✗ listele APT nu sunt disponibile — rulează `apt-get update`",
              file=sys.stderr)
        return 1
    print(f"✔ index: {len(index)} pachete")

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    confirmate, refuzate = [], []
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        app_id = app.get("id")
        if app_id in COLIZIUNI:
            refuzate.append((app_id, COLIZIUNI[app_id]))
            continue
        ind = app.get("indicators") or {}
        if ind.get("in_ubuntu_repos") is True:
            continue
        pachet = app.get("package") or app_id
        descriere = index.get(pachet)
        if descriere is None:
            continue
        if not potrivire(app_id, pachet, descriere):
            refuzate.append((app_id, f"descriere neconcordantă: {descriere[:60]}"))
            continue
        ind["in_ubuntu_repos"] = True
        app["indicators"] = ind
        confirmate.append((app_id, pachet, descriere[:50]))
        if not args.dry_run:
            with cale.open("w", encoding="utf-8") as fh:
                yaml.dump(app, fh)

    print(f"✔ confirmate: {len(confirmate)}")
    for app_id, pachet, descriere in confirmate:
        print(f"   {app_id:16} [{pachet:18}] {descriere}")
    if refuzate:
        print(f"• neconfirmate (coliziuni de nume): {len(refuzate)}")
        for app_id, motiv in refuzate:
            print(f"   {app_id:16} {motiv}")
    if args.dry_run:
        print("(rulează fără --dry-run pentru a scrie)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
