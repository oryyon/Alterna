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


def _generează(tmp: Path, db: Path) -> Path:
    """Generează pagina dintr-un catalog dat (nu din rădăcină).

    `catalog.db` nu există neapărat în rădăcina repo-ului (pe runner se
    construiește într-un fișier temporar), deci îi dăm calea explicită.
    """
    rezultat = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_site.py"),
         "--out", str(tmp), "--db", str(db)],
        capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    assert rezultat.returncode == 0, rezultat.stdout + rezultat.stderr
    return tmp


def test_pagina_se_generaza(tmp_path, built_db):
    ieșire = _generează(tmp_path, built_db)
    for nume in ("index.html", "style.css", "catalog.js", "catalog.json"):
        assert (ieșire / nume).exists(), nume


def test_pagina_are_toate_aplicatiile(tmp_path, built_db, catalog):
    ieșire = _generează(tmp_path, built_db)
    date = json.loads((ieșire / "catalog.json").read_text(encoding="utf-8"))
    aplicatii = date["aplicatii"]
    assert len(aplicatii) == catalog.app_count
    assert {a["id"] for a in aplicatii} == {a["id"] for a in catalog.search()}


def test_pagina_are_toate_categoriile(tmp_path, built_db, catalog):
    ieșire = _generează(tmp_path, built_db)
    html = (ieșire / "index.html").read_text(encoding="utf-8")
    import html as html_mod

    for slug, nume in catalog.categories:
        assert f'value="{slug}"' in html, slug
        # numele e escapat in HTML (& devine &amp;)
        assert html_mod.escape(nume) in html, nume


def test_fiecare_card_are_sursa(tmp_path, built_db):
    """Fiecare aplicație din pagină are linkul către sursa ei."""
    ieșire = _generează(tmp_path, built_db)
    html = (ieșire / "index.html").read_text(encoding="utf-8")
    assert html.count('rel="noopener"') >= 100


def test_textele_sunt_in_romana(tmp_path, built_db):
    """Interfața paginii e în română, cu diacritice."""
    ieșire = _generează(tmp_path, built_db)
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


class TestPaginiDetaliu:
    """Fiecare aplicație are pagină proprie, cu faptele și mini-matricea."""

    def test_fiecare_aplicatie_are_pagina_de_detaliu(self, tmp_path, built_db,
                                                      catalog):
        ieșire = _generează(tmp_path, built_db)
        pagini = list((ieșire / "app").glob("*.html"))
        assert len(pagini) == catalog.app_count, (
            f"{len(pagini)} pagini pentru {catalog.app_count} aplicații")

    def test_pagina_de_detaliu_are_faptele_si_sursele(self, tmp_path, built_db):
        ieșire = _generează(tmp_path, built_db)
        html = (ieșire / "app" / "gimp.html").read_text(encoding="utf-8")
        assert "Indicatori obiectivi" in html
        assert "Surse (verificabile)" in html
        assert "gimp.org" in html, "sursa oficială nu e citată"
        assert "apt://gimp" in html, "linkul APT lipsește"
        assert "⟳" in html or "✓" in html, "marcajele de certitudine lipsesc"

    def test_mini_matrice_este_pe_pagina(self, tmp_path, built_db):
        """Coloana aplicației din matricea categoriei, cu rândurile canonice."""
        ieșire = _generează(tmp_path, built_db)
        html = (ieșire / "app" / "gimp.html").read_text(encoding="utf-8")
        assert "Funcționalități" in html
        assert "Editare de imagini raster (pixeli)" in html
        assert "✓ gratuit" in html
        assert "Matricea completă" in html

    def test_captura_are_fisier_si_sursa(self, tmp_path, built_db, catalog):
        ieșire = _generează(tmp_path, built_db)
        for app in catalog.search():
            if not app.get("screenshot"):
                continue
            html = (ieșire / "app" / f"{app['id']}.html").read_text(encoding="utf-8")
            assert "<img" in html, app["id"]
            # calea din pagină (site/app/) trebuie să resolveze spre fișier
            import re

            potrivire = re.search(r'src="([^"]+)"', html)
            assert potrivire, app["id"]
            imagine = (ieșire / "app" / potrivire.group(1)).resolve()
            assert imagine.exists(), (
                f"{app['id']}: imaginea {potrivire.group(1)} nu e la locul ei")
            assert "atribuirea imaginilor" in html, app["id"]

    def test_credite_lista_toate_capturile(self, tmp_path, built_db, catalog):
        ieșire = _generează(tmp_path, built_db)
        html = (ieșire / "credite.html").read_text(encoding="utf-8")
        cu_captura = [a for a in catalog.search() if a.get("screenshot")]
        assert cu_captura, "nicio aplicație cu captură"
        for app in cu_captura[:20]:
            assert app["name"] in html, app["id"]

    def test_catalog_json_are_taxonomia_si_functiile(self, tmp_path, built_db):
        ieșire = _generează(tmp_path, built_db)
        date = json.loads((ieșire / "catalog.json").read_text(encoding="utf-8"))
        assert date["taxonomie"], "taxonomia lipsește din JSON"
        assert "graphics" in date["taxonomie"]
        cu_functii = [a for a in date["aplicatii"] if a.get("features")]
        assert cu_functii, "nicio aplicație cu valori de funcționalitate"
