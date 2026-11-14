"""Entry point de consolă pentru verificarea pachetului construit.

Executabilul grafic ``Alterna`` este compilat cu ``--windowed`` (fără consolă
pe Windows/Linux GUI), deci stdout nu este fiabil pentru diagnosticare. Acest
entry point este ambalat separat ca ``Alterna-selftest`` și oferă un raport pe
stdout plus un cod de ieșire utilizabil în CI.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import run_selftest  # noqa: E402
from app.paths import default_catalog_path  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(run_selftest(default_catalog_path()))
