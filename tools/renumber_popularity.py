#!/usr/bin/env python3
"""Alterna — renumerotă `popularity` după extinderea catalogului.

`popularity` e ordinea editorială a catalogului (multiplu de 10, unic). Când
se adaugă aplicații, valorile se ciocnesc — și build-ul avertizează.

Instrumentul păstrează **ordinea relativă** a aplicațiilor existente (nimeni
nu se mută înaintea altuia) și le intercalează pe cele noi după valoarea din
semință, cu departajare alfabetică în interiorul aceluiași nivel. Apoi
renumerotează 10, 20, 30… de la zero.

Utilizare:
    python tools/renumber_popularity.py --dry-run
    python tools/renumber_popularity.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ruamel.yaml import YAML  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "apps"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="doar raportul, nu scrie fișierele")
    args = parser.parse_args()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096

    intrări = []
    for cale in sorted(DATA.glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        intrări.append((cale, app, int(app.get("popularity") or 0)))

    # ordine: popularitate, apoi id (departajare deterministă)
    intrări.sort(key=lambda t: (t[2], t[1].get("id", "")))

    schimbate = 0
    for poziție, (cale, app, vechi) in enumerate(intrări, start=1):
        nou = poziție * 10
        if nou == vechi:
            continue
        app["popularity"] = nou
        schimbate += 1
        if not args.dry_run:
            with cale.open("w", encoding="utf-8") as fh:
                yaml.dump(app, fh)

    print(f"✔ {len(intrări)} aplicații, {schimbate} valori renumerotate "
          f"(multipli de 10, începând cu 10)")
    if args.dry_run:
        print("(rulează fără --dry-run pentru a scrie)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
