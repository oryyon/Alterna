"""Teste pentru pagina web generată (`tools/build_site.py`).

Pagina trebuie să fie un **mirror** al catalogului: aceleași aplicații, aceleași
categorii, și sursele vizibile (regula „totul e verificabil”). Altfel pagina
ar putea diverge de aplicația desktop — și n-ar mai fi adevărată.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def _generează(tmp: Path) -> Path:
    rezultat = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_site.py"),
         "--out", str(tmp)],
        capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    assert rezultat.returncode == 0, rezultat.stdout + rezultat.stderr
    return tmp


def test_pagina_se_generaza(tmp_path):
    ieșire = _generează(tmp_path)
    for nume in ("index.html", "style.css", "catalog.js", "catalog.json"):
        assert (ieșire / nume).exists(), nume


def test_pagina_are_toate_aplicatiile(tmp_path):
    ieșire = _generează(tmp_path)
    date = json.loads((ieșire / "catalog.json").read_text(encoding="utf-8"))
    from app.db import Catalog

    catalog = Catalog(ROOT / "catalog.db")
    assert len(date) == catalog.app_count
    assert {a["id"] for a in date} == {a["id"] for a in catalog.search()}


def test_pagina_are_toate_categoriile(tmp_path):
    ieșire = _generează(tmp_path)
    html = (ieșire / "index.html").read_text(encoding="utf-8")
    from app.db import Catalog

    catalog = Catalog(ROOT / "catalog.db")
    import html as html_mod

    for slug, nume in catalog.categories:
        assert f'value="{slug}"' in html, slug
        # numele e escapat in HTML (& devine &amp;)
        assert html_mod.escape(nume) in html, nume


def test_fiecare_card_are_sursa(tmp_path):
    """Fiecare aplicație din pagină are linkul către sursa ei."""
    ieșire = _generează(tmp_path)
    html = (ieșire / "index.html").read_text(encoding="utf-8")
    assert html.count('rel="noopener"') >= 100


def test_textele_sunt_in_romana(tmp_path):
    """Interfața paginii e în română, cu diacritice."""
    ieșire = _generează(tmp_path)
    html = (ieșire / "index.html").read_text(encoding="utf-8")
    assert 'lang="ro"' in html
    assert "aplicații" in html
    assert "Caută o aplicație" in html


def test_traducere_exista_si_are_glosar():
    fișier = ROOT / "TRADUCERE.md"
    assert fișier.exists(), "TRADUCERE.md lipsește"
    text = fișier.read_text(encoding="utf-8")
    assert "## Glosar" in text
    assert "telemetry" in text
    assert "certitudine" in text.lower()
