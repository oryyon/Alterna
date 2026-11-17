"""Teste pentru capturile de ecran (Wikidata P18 → Wikimedia Commons).

Capturile sunt resurse ale unor terți: fiecare trebuie să aibă **fișierul
prezent** și **sursa citată**, ca interfața să poată arăta de unde vine
imaginea (sec. 8 — „totul e verificabil”).
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
IESIRI = ROOT / "data" / "screenshots"


@pytest.fixture(scope="module")
def aplicatii():
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.allow_duplicate_keys = False
    rezultat = {}
    for cale in sorted((ROOT / "data" / "apps").glob("*.yaml")):
        app = yaml.load(cale.read_text(encoding="utf-8"))
        rezultat[app["id"]] = app
    return rezultat


def test_exista_capturi(aplicatii):
    cu = [a for a in aplicatii.values() if a.get("screenshot")]
    assert len(cu) >= 50, f"doar {len(cu)} capturi"


def test_fiecare_captura_exista_pe_disc(aplicatii):
    lipsa = []
    for app_id, app in aplicatii.items():
        cale = app.get("screenshot")
        if not cale:
            continue
        if not (ROOT / "data" / cale).exists():
            lipsa.append(app_id)
    assert not lipsa, f"capturi fără fișier: {lipsa[:5]}"


def test_sursa_capturii_e_citata(aplicatii):
    """Linkul către fișierul original trebuie să fie în `sources`."""
    fara = []
    for app_id, app in aplicatii.items():
        if not app.get("screenshot"):
            continue
        if not any("commons.wikimedia.org" in str(s)
                   for s in app.get("sources") or []):
            fara.append(app_id)
    assert not fara, f"capturi fără sursă: {fara[:5]}"


def test_atribuirea_e_documentata(aplicatii):
    """Fișierul de atribuire există și listă aplicațiile cu captură."""
    cu = [app_id for app_id, a in aplicatii.items() if a.get("screenshot")]
    atribute = IESIRI / "README.md"
    assert atribute.exists(), "lipsă data/screenshots/README.md (atribuire)"
    text = atribute.read_text(encoding="utf-8")
    for app_id in cu[:10]:
        assert app_id in text, f"{app_id} nu e în tabelul de atribuire"


def test_imaginile_sunt_rezonabil_de_mici():
    """O captură uriașă ar umfla pachetul aplicației."""
    mari = [p.name for p in IESIRI.glob("*")
            if p.suffix in (".png", ".jpg") and p.stat().st_size > 600_000]
    assert not mari, f"imagini prea mari: {mari[:5]}"
