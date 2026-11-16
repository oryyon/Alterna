#!/usr/bin/env bash
# Alterna — reîmprospătarea completă a catalogului, în ordinea corectă.
#
# Ordinea contează: fiecare pas rescrie fișierele YAML, deci un pas ulterior
# poate suprascrie ce a scris unul anterior. De aceea pasii sunt în ordinea
# „import → indicatori → confirmări → dimensiuni → logo-uri → limbă → pachete”.
#
#   import_apps.py            scrie intrările noi (doar dacă există semințe)
#   refresh_indicators.py     popcon, stele, ultima versiune, repo Ubuntu
#   confirm_packages.py       confirmă manual `in_ubuntu_repos` (vezi coliziuni)
#   refresh_sizes.py          dimensiunea la instalare, măsurată din arhivă
#   fetch_logos.py            logo-urile reale
#   check_ro.py               limba română, confirmată din fișierele de traducere
#   check_installed_sources.py  numele snap / Flatpak, confirmate în registre
#   build_catalog.py          catalog.db + validări
#
# Utilizare:
#   bash tools/refresh_all.sh            # tot
#   bash tools/refresh_all.sh --import   # doar importul (restul rămâne)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3

do_import=0
[ "${1:-}" = "--import" ] && do_import=1

if [ "$do_import" = "1" ] && compgen -G "tools/seminte/*.yaml" > /dev/null; then
  printf '\n=== [1/8] Import din semințe (Wikidata pentru datele obiective) ===\n'
  "$PYTHON" -u tools/import_apps.py --overwrite
  "$PYTHON" -u tools/renumber_popularity.py
fi

printf '\n=== [2/8] Indicatori (popcon / GitHub / repo Ubuntu) ===\n'
"$PYTHON" -u tools/refresh_indicators.py

printf '\n=== [3/8] Confirmarea manuală a pachetelor ===\n'
"$PYTHON" -u tools/confirm_packages.py

printf '\n=== [4/8] Dimensiuni la instalare (din arhivă) ===\n'
"$PYTHON" -u tools/refresh_sizes.py

printf '\n=== [5/8] Logo-uri ===\n'
"$PYTHON" -u tools/fetch_logos.py

printf '\n=== [6/8] Limba română ===\n'
"$PYTHON" -u tools/check_ro.py

printf '\n=== [7/8] Surse snap / Flatpak ===\n'
"$PYTHON" -u tools/check_installed_sources.py

printf '\n=== [8/8] Build + validări ===\n'
"$PYTHON" -u tools/build_catalog.py
