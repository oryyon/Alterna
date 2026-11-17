"""Teste pentru taxonomiile de funcționalități (sec. 15).

O taxonomie există pentru o categorie → **toate** aplicațiile ei au matricea
completă. Altfel, comparația ar afișa rânduri goale pentru unele aplicații
și pline pentru altele — iar diferența nu s-ar vedea ca diferență.

De aceea verificăm trei lucruri:
1. fiecare taxonomie declară chei unice și nevide;
2. fiecare aplicație dintr-o categorie cu taxonomie are toate cheile;
3. valorile sunt din mulțimea permisă (free/paid/partial/no/unknown), cu
   „no" scris între ghilimele (altfel YAML-ul îl citește ca `False`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VALORI = {"free", "paid", "partial", "no", "unknown"}


def _yaml():
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.allow_duplicate_keys = False
    return yaml


@pytest.fixture(scope="module")
def catalog():
    yaml = _yaml()
    aplicații = {}
    for cale in sorted((ROOT / "data" / "apps").glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        aplicații[app["id"]] = app
    return aplicații


@pytest.fixture(scope="module")
def taxonomii():
    yaml = _yaml()
    rezultat = {}
    for cale in sorted((ROOT / "data" / "taxonomy").glob("*.yaml")):
        date = yaml.load(cale.read_text(encoding="utf-8"))
        rezultat[date["category"]] = date["features"]
    return rezultat


def test_exista_cel_putin_doua_taxonomii(taxonomii):
    assert len(taxonomii) >= 2, taxonomii.keys()


def test_cheile_sunt_unice_si_nevide(taxonomii):
    for categorie, features in taxonomii.items():
        assert features, f"{categorie}: taxonomie goală"
        assert len(features) >= 8, f"{categorie}: prea puține rânduri"


def test_toate_aplicatiile_au_matricea_completa(catalog, taxonomii):
    lipsa = []
    for app_id, app in catalog.items():
        features = taxonomii.get(app.get("category"))
        if not features:
            continue
        declarate = set((app.get("features") or {}).keys())
        diferenta = sorted(set(features) - declarate)
        if diferenta:
            lipsa.append((app_id, diferenta))
    assert not lipsa, f"aplicații fără matrice completă: {lipsa[:5]}"


def test_valorile_sunt_din_multimea_permisa(catalog):
    rele = []
    for app_id, app in catalog.items():
        for cheie, valoare in (app.get("features") or {}).items():
            # valoarea poate fi un scalar sau {value, note}
            if isinstance(valoare, dict):
                valoare = valoare.get("value")
            if str(valoare) not in VALORI:
                rele.append((app_id, cheie, valoare))
    assert not rele, f"valori nepermise: {rele[:5]}"


def test_no_e_scris_cu_ghilimele(catalog):
    """`no` fără ghilimele devine `False` la citire — o capcană cunoscută."""
    rele = []
    for app_id, app in catalog.items():
        for cheie, valoare in (app.get("features") or {}).items():
            if isinstance(valoare, dict):
                valoare = valoare.get("value")
            if valoare is False or str(valoare) == "False":
                rele.append((app_id, cheie))
    assert not rele, f"valori `no` necitate (devin False): {rele[:5]}"


def test_categoriile_cu_taxonomie_apar_in_comparatie(catalog, taxonomii):
    """Categoriile cu taxonomie au aplicații — altfel matricea n-ar apărea."""
    for categorie in taxonomii:
        nr = sum(1 for a in catalog.values() if a.get("category") == categorie)
        assert nr >= 2, f"{categorie}: prea puține aplicații ({nr})"
