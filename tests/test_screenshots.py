"""Teste pentru capturile de ecran (Wikidata P18 → Wikimedia Commons).

Capturile sunt resurse ale unor terți: fiecare trebuie să aibă **fișierul
prezent** și **sursa citată**, ca interfața să poată arăta de unde vine
imaginea (sec. 8 — „totul e verificabil”).
"""

from __future__ import annotations

import urllib.parse
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
    """Linkul către fișierul original trebuie să fie în `sources`.

    Sunt trei surse acceptate: Wikimedia Commons (proprietatea P18 din
    Wikidata), depozitul oficial GitHub al aplicației (README-ul proiectului)
    și site-ul oficial al aplicației (imaginea de prezentare, og:image).
    """
    fara = []
    for app_id, app in aplicatii.items():
        if not app.get("screenshot"):
            continue
        surse = [str(s) for s in app.get("sources") or []]
        domeniu = urllib.parse.urlparse(app.get("website") or "").netloc
        if not any("commons.wikimedia.org" in s or "github.com" in s
                   or (domeniu and domeniu in s) for s in surse):
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


def test_atribuirea_acopera_toate_capturile():
    """Fiecare aplicație cu captură trebuie să aibă rând în tabel.

    Tabelul se generează din catalog (`tools/build_screenshots_attribution.py`);
    dacă un instrument de descărcare l-ar suprascrie, rândurile celorlalte
    surse ar dispărea — exact ce s-a întâmplat (51 de aplicații fără
    atribuire, prins de acest test).
    """
    text = (IESIRI / "README.md").read_text(encoding="utf-8")
    lipsa = []
    for cale in sorted((ROOT / "data" / "apps").glob("*.yaml")):
        from ruamel.yaml import YAML

        app = YAML().load(cale.read_text(encoding="utf-8"))
        if app.get("screenshot") and app["id"] not in text:
            lipsa.append(app["id"])
    assert not lipsa, f"capturi fără atribuire: {lipsa[:8]}"
