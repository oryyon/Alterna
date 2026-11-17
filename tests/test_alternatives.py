"""Teste pentru relațiile de alternative (verificarea semantică).

Instrumentul `tools/check_alternatives.py` verifică trei lucruri care pot fi
verificate mecanic: existența alternativei, simetria relației și faptul că o
relație între categorii diferite e justificată explicit. Testele de aici
păstrează invariantul în CI — o relație care se strică într-un PR trebuie să
pică, nu să treacă nestingherită.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools.check_alternatives import justificat

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def catalog_yaml():
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.allow_duplicate_keys = False
    aplicații = {}
    for cale in sorted((ROOT / "data" / "apps").glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        aplicații[app["id"]] = app
    return aplicații


class TestRelatiiAlternative:
    def test_fiecare_alternativa_exista(self, catalog_yaml):
        for app_id, app in catalog_yaml.items():
            for alt in app.get("alternatives") or []:
                assert alt in catalog_yaml, \
                    f"{app_id}: alternativa '{alt}' nu există în catalog"

    def test_nicio_aplicatie_nu_se_alternativeaza_cu_propria(self, catalog_yaml):
        for app_id, app in catalog_yaml.items():
            assert app_id not in (app.get("alternatives") or []), app_id

    def test_nicio_alternativa_duplicata(self, catalog_yaml):
        for app_id, app in catalog_yaml.items():
            alts = list(app.get("alternatives") or [])
            assert len(alts) == len(set(alts)), \
                f"{app_id}: are alternative duplicate"

    def test_relatiile_sunt_simetrize(self, catalog_yaml):
        """Dacă A e alternativă pentru B, și B e alternativă pentru A."""
        nesimetrice = []
        for app_id, app in catalog_yaml.items():
            for alt in app.get("alternatives") or []:
                if alt not in catalog_yaml:
                    continue
                if app_id not in (catalog_yaml[alt].get("alternatives") or []):
                    nesimetrice.append((app_id, alt))
        assert not nesimetrice, \
            f"relații într-un singur sens: {nesimetrice[:10]}"

    def test_relatiile_intre_categorii_sunt_justificate(self, catalog_yaml):
        nejustificate = []
        for app_id, app in catalog_yaml.items():
            for alt in app.get("alternatives") or []:
                if alt not in catalog_yaml:
                    continue
                cat_a = app.get("category")
                cat_b = catalog_yaml[alt].get("category")
                if cat_a != cat_b and not justificat(cat_a, cat_b):
                    nejustificate.append((app_id, alt, cat_a, cat_b))
        assert not nejustificate, \
            f"relații între categorii nejustificate: {nejustificate[:10]}"

    def test_instrumentul_raporteaza_starea_curata(self):
        """Instrumentul însuși trebuie să închidă raportul fără probleme."""
        import subprocess

        rezultat = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_alternatives.py")],
            capture_output=True, text=True, cwd=str(ROOT))
        assert rezultat.returncode == 0, rezultat.stdout + rezultat.stderr
        import re

        # proprietăți, nu numere înghețate: 100% simetrice, 0 nejustificate
        sim = re.search(r"simetrice: (\d+)/(\d+)", rezultat.stdout)
        assert sim, rezultat.stdout
        assert sim.group(1) == sim.group(2), rezultat.stdout
        nejust = re.search(r"din care (\d+) nejustificate", rezultat.stdout)
        assert nejust and nejust.group(1) == "0", rezultat.stdout
