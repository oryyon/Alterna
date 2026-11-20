#!/usr/bin/env python3
"""Alterna — tabelul de atribuire pentru capturile de ecran (data/screenshots/README.md).

Fiecare captură e resursă a unui terț, deci sursa trebuie citată (sec. 8 — „totul
e verificabil”). Tabelul se **regenerează** din fișierele aplicațiilor: pentru
fiecare captură se caută sursa (Wikimedia Commons sau depozitul oficial GitHub),
iar licența se ia din API-ul GitHub (cu cache local, ca să nu se ceară de fiecare
dată aceleași 100 de adrese).

Utilizare:
    python tools/build_screenshots_attribution.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"
IESIRI = ROOT / "data" / "screenshots"
CACHE = Path.home() / ".cache" / "alterna" / "licente-repo.json"
TITLU = "## Din README-ul oficial al proiectului (GitHub)"

UA = {"User-Agent": "Alterna/0.2 (+https://github.com/oryyon/Alterna)"}
GH_BLOB = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/blob/")


def cere_json(url: str, token: str = "") -> dict | None:
    antet = dict(UA)
    if token:
        antet["Authorization"] = f"Bearer {token}"
    try:
        cerere = urllib.request.Request(url, headers=antet)
        with urllib.request.urlopen(cerere, timeout=30) as răspuns:
            return json.loads(răspuns.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    yaml = YAML()
    yaml.preserve_quotes = True

    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except ValueError:
            cache = {}

    github: list[tuple[str, str, str, str]] = []
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        if not app.get("screenshot"):
            continue
        for sursa in app.get("sources") or []:
            potrivire = GH_BLOB.match(str(sursa))
            if not potrivire:
                continue
            repo = f"{potrivire.group(1)}/{potrivire.group(2)}"
            cheie = repo.lower()
            if cheie not in cache:
                meta = cere_json(f"https://api.github.com/repos/{repo}", token) or {}
                cache[cheie] = ((meta.get("license") or {}).get("spdx_id") or "")
            github.append((app["id"], repo, str(sursa), cache[cheie]))
            break

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                     encoding="utf-8")

    cu = IESIRI / "README.md"
    if cu.exists():
        linii = cu.read_text(encoding="utf-8").splitlines()
    else:
        linii = ["# Capturi de ecran", "",
                 "Nu fac parte din pachetul aplicației; sunt afișate în "
                 "aplicație cu atribuirea sursei (linkul apare în pagina de "
                 "detalii, la „Surse”)."]
    # secțiunea veche e înlocuită (dacă există)
    if TITLU in linii:
        linii = linii[:linii.index(TITLU)]

    if github:
        linii.append("")
        linii.append(TITLU)
        linii.append("")
        linii.append("Descărcate de "
                     "[`tools/fetch_screenshots_github.py`](../tools/fetch_screenshots_github.py) "
                     "din README-ul depozitului oficial al aplicației.")
        linii.append("")
        linii.append("| Aplicație | Depozit | Imagine | Licență |")
        linii.append("|---|---|---|---|")
        for app_id, repo, sursa, licenta in github:
            linii.append(f"| {app_id} | {repo} | {sursa} | {licenta or '—'} |")
    cu.write_text("\n".join(linii) + "\n", encoding="utf-8")
    print(f"atribuire: {len(github)} capturi din README-ul oficial, "
          f"{len(cache)} depozite în cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
