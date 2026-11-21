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


class TestComparatie:
    """Tabelul comparativ de pe site (aceleași criterii ca în aplicație)."""

    def test_paginile_comparatie_exista(self, tmp_path, built_db):
        ieșire = _generează(tmp_path, built_db)
        assert (ieșire / "compara.html").exists()
        assert (ieșire / "compara.js").exists()
        html = (ieșire / "compara.html").read_text(encoding="utf-8")
        assert 'src="compara.js"' in html
        assert 'href="catalog.json"' not in html  # datele vin prin fetch()
        assert "catalog.json" in (ieșire / "compara.js").read_text(encoding="utf-8")

    def test_js_aplica_regula_avantajului_objectiv(self, tmp_path, built_db):
        """Avantajul se evidențiază doar pe criterii verificate."""
        ieșire = _generează(tmp_path, built_db)
        js = (ieșire / "compara.js").read_text(encoding="utf-8")
        assert "avantaj" in js
        # certitudinea e citită din catalog (⟳/✓) — nu se inventează
        assert "confidence" in js
        assert "auto" in js and "manual" in js

    def test_matricea_este_inclusa_pentru_aceeasi_categorie(self, tmp_path,
                                                            built_db):
        ieșire = _generează(tmp_path, built_db)
        js = (ieșire / "compara.js").read_text(encoding="utf-8")
        assert "taxonomie" in js
        assert "FUNCȚIONALITĂȚI" in js
        assert "free" in js and "partial" in js and "unknown" in js

    def test_export_csv_si_markdown(self, tmp_path, built_db):
        ieșire = _generează(tmp_path, built_db)
        js = (ieșire / "compara.js").read_text(encoding="utf-8")
        assert "text/csv" in js and "text/markdown" in js


class TestComparatieJs:
    """Logica tabelului comparativ, rulată de fapt (node + DOM minimal).

    Bug raportat de utilizator: se puteau bifa aplicațiile, dar tabelul nu
    apărea — `rand()` referința o variabilă inexistentă, iar `ReferenceError`
    era înghițit în callback. Testul execută JS-ul și verifică desenarea.
    """

    def test_js_deseneaza_tabelul(self, tmp_path, built_db):
        import shutil
        import subprocess

        node = shutil.which("node") or shutil.which("nodejs")
        if not node:
            import pytest

            pytest.skip("node nu e instalat — testul JS nu poate rula")

        ieșire = _generează(tmp_path, built_db)
        rezultat = subprocess.run(
            [node, str(ROOT / "tools" / "test_compara_node.js"),
             str(ieșire / "catalog.json")],
            capture_output=True, text=True, cwd=str(ROOT), timeout=120)
        assert rezultat.returncode == 0, (
            rezultat.stdout + rezultat.stderr)
        assert "OK" in rezultat.stdout, rezultat.stdout
