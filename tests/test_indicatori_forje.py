"""Teste pentru detectarea depozitelor pe forje diferite (stele).

`tools/refresh_indicators.py` citește stelele de pe GitHub, dar multe aplicații
FOSS își au repo-ul pe altă forjă: GitLab (comunitar, GNOME, XFCE, Tor) sau
Gitea (Codeberg, KDE invent). Fără suport pentru ele, indicatorul „stele”
rămâne gol, deși valoarea e publică și verificabilă.

Testele sunt **offline**: verifică detectarea adreselor, nu rețeaua.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _instrument():
    """Încarcă unealta (e un script, nu un modul de pachet)."""
    spec = importlib.util.spec_from_file_location(
        "refresh_indicators", ROOT / "tools" / "refresh_indicators.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


#: Căi de proiect care nu mai există pe forja lor (API-ul dă 404) — de aceea
#: indicatorul „stele” rămâne gol, în loc de o valoare inventată.
PROIECTE_INEXISTENTE = {
    "lazarus",  # gitlab.com/freepascal.org/lazarus → 404 (proiect mutat/renumat)
}


@pytest.fixture(scope="module")
def unealta():
    return _instrument()


class TestDetectareRepo:
    """Dintr-o adresă de sursă se deduce forja și calea proiectului."""

    @pytest.mark.parametrize("url,asteptat", [
        ("https://github.com/marktext/marktext",
         ("github.com", "github", "marktext/marktext")),
        ("https://gitlab.com/inkscape/inkscape",
         ("gitlab.com", "gitlab", "inkscape/inkscape")),
        ("https://gitlab.gnome.org/GNOME/baobab.git",
         ("gitlab.gnome.org", "gitlab", "GNOME/baobab")),
        ("https://gitlab.xfce.org/xfce/thunar",
         ("gitlab.xfce.org", "gitlab", "xfce/thunar")),
        ("https://codeberg.org/dnephin/PyMOL.git",
         ("codeberg.org", "gitea", "dnephin/PyMOL")),
        ("https://invent.kde.org/utilities/ark",
         ("invent.kde.org", "gitea", "utilities/ark")),
    ])
    def test_recunoaste_forja(self, unealta, url, asteptat):
        assert unealta.repo_din_sursa(url) == asteptat

    def test_sufixul_git_e_eliminat(self, unealta):
        """„GNOME/baobab.git” și „GNOME/baobab” sunt același proiect."""
        assert unealta.repo_din_sursa(
            "https://gitlab.gnome.org/GNOME/baobab.git")[2] == "GNOME/baobab"

    def test_adresa_fara_repo_nu_e_detectata(self, unealta):
        assert unealta.repo_din_sursa("https://www.gimp.org/") is None
        assert unealta.repo_din_sursa("") is None


class TestAplicațiiCuStele:
    """În catalog, orice aplicație cu repo cunoscut are stele (sau le are
    pentru că forja nu are API — cazul Launchpad/SourceForge)."""

    def test_aplicatiile_cu_repo_gitlab_au_stele(self):
        """Pentru forjele cu API public, stelele sunt completate.

        Excepții documentate: Launchpad și SourceForge nu au API de stele,
        invent.kde.org cere autentificare, iar un grup GitLab (ex.:
        freepascal.org/lazarus) nu e un proiect — API-ul dă 404.
        """
        from ruamel.yaml import YAML

        yaml = YAML()
        fara = []
        for cale in sorted((ROOT / "data" / "apps").glob("*.yaml")):
            app = yaml.load(cale.read_text(encoding="utf-8"))
            indicatori = app.get("indicators") or {}
            if indicatori.get("stars") is not None:
                continue
            surse = [str(s) for s in app.get("sources") or []]
            forja = None
            for sursa in surse:
                for domeniu in ("gitlab.com/", "gitlab.gnome.org/",
                                "gitlab.xfce.org/", "codeberg.org/"):
                    if domeniu in sursa:
                        forja = domeniu
                        break
                if forja:
                    break
            if not forja:
                continue
            # grup GitLab (ex.: kicad, freepascal.org/lazarus) — nu e proiect,
            # deci API-ul dă 404
            cale = " ".join(s for s in surse if forja in s).split(forja)[-1].strip("/")
            if cale.count("/") < 1:
                continue  # grup, nu proiect
            if app["id"] in PROIECTE_INEXISTENTE:
                continue  # calea nu mai există pe forjă (404)
            fara.append(app["id"])
        assert not fara, f"repo GitLab/Codeberg, dar fără stele: {fara[:8]}"
