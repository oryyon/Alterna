"""Teste pentru importul de aplicații (extinderea catalogului).

Semințele (`tools/seminte/*.yaml`) sunt sursa editorială a tranzelor, iar
`tools/import_apps.py` completează datele obiective din Wikidata. Testele
verifică cele două jumătăți: semințele sunt coerente, iar importul produce
intrări valide.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SEMINTE = ROOT / "tools" / "seminte"
APPS = ROOT / "data" / "apps"


def _semințe() -> list[dict]:
    import yaml

    intrări: list[dict] = []
    for fișier in sorted(SEMINTE.glob("*.yaml")):
        date = yaml.safe_load(fișier.read_text(encoding="utf-8")) or []
        for intrare in date:
            intrare["_fișier"] = fișier.name
            intrări.append(intrare)
    return intrări


class TestSeminte:
    def test_exista_semințe(self):
        assert SEMINTE.is_dir(), "directorul de semințe lipsește"

    def test_id_uri_unice(self):
        id_uri = [s["id"] for s in _semințe()]
        duble = {i for i in id_uri if id_uri.count(i) > 1}
        assert not duble, f"id-uri duplicate în semințe: {duble}"

    def test_fiecare_intrare_are_campurile_obligatorii(self):
        for s in _semințe():
            for câmp in ("id", "name", "category", "description", "tags",
                         "platforms", "alternatives"):
                assert câmp in s, f"{s['id']}: lipseste {câmp}"
            assert s["description"].strip(), s["id"]

    def test_alternativele_exista_in_catalog(self):
        """O alternativă care nu există ar strica build-ul (validat la build)."""
        cunoscute = {p.stem for p in APPS.glob("*.yaml")}
        cunoscute |= {s["id"] for s in _semințe()}
        for s in _semințe():
            for alternativa in s["alternatives"]:
                assert alternativa in cunoscute, \
                    f"{s['id']}: alternativa '{alternativa}' nu există"

    def test_nicio_aplicatie_nu_are_ca_alternativa_proprie(self):
        for s in _semințe():
            assert s["id"] not in s["alternatives"], s["id"]


class TestInstrument:
    def test_sintaxa(self):
        ast.parse((ROOT / "tools" / "import_apps.py").read_text(encoding="utf-8"))

    def test_an_din_timp(self):
        from tools.import_apps import an_din_timp

        assert an_din_timp("+2005-06-21T00:00:00Z") == 2005
        assert an_din_timp("+1992-00-00T00:00:00Z") == 1992
        assert an_din_timp(None) is None

    def test_tip_licenta(self):
        from tools.import_apps import tip_licență

        assert tip_licență("GPL-2.0") == "foss"
        assert tip_licență("GNU Lesser General Public License v3") == "foss"
        assert tip_licență("MIT License") == "foss"
        assert tip_licență("Proprietary") == "commercial"
        assert tip_licență("Unknown") is None

    def test_platforme_recognoscute(self):
        from tools.import_apps import platforme_din_wikidata

        assert platforme_din_wikidata(["Q9135", "Q1066", "Q999999"]) == \
            ["linux", "windows"]


class TestCatalogExtins:
    def test_catalogul_are_peste_150_aplicatii(self, catalog):
        assert catalog.app_count >= 150, catalog.app_count

    def test_toate_aplicatiile_au_site_si_dezvoltator(self, catalog):
        """Datele obiective trebuie să fie complete — nu goluri."""
        for app in catalog.search():
            assert app["website"].startswith("https://"), app["id"]
            assert (app["developer"] or "").strip(), app["id"]
