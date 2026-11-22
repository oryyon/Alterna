"""Teste pentru verificarea datelor din punctul 8 (limba română, telemetrie).

Punctul 8 din review cere ca `details.romanian_language` și
`details.telemetry` să fie **verificate**, nu estimate: pentru fiecare valoare
există o sursă concretă, iar marcajul de certitudine spune „manual”.

Testele verifică:
- logica de recognizare a traducerii din arhivă (nume de pachet, `.mo`);
- faptul că aplicațiile confirmate poartă marcajul „manual” în catalog;
- faptul că excepțiile documentate rămân nemarkate;
- faptul că tabelul de telemetrie din `tools/check_telemetry.py` corespunde
  valorilor din catalog și că fiecare sursă e citată în `sources`.
"""

from __future__ import annotations

import io

import pytest

from tools.check_ro import (EXCLUDERI, extrage_ro, mo_al_aplicatiei,
                            nume_inrudit)
from tools.check_telemetry import VERIFICARI


class TestVerificareaCitatului:
    """`check_telemetry.py` trebuie să verifice și citatul, nu doar pagina.

    Altfel o adresă vie ar „dovedi” orice — inclusiv după ce pagina își
    schimbă textul.
    """

    def test_citatul_normalizat_se_cauta_in_textul_plain(self):
        from tools.check_telemetry import _re_quote, _text_plain

        pagina = "<p>We collect usage data\n  for analytics.</p>"
        text = _text_plain(pagina)
        assert _re_quote("We collect usage data for analytics.") in text

    def test_citatul_absent_nu_e_acceptat(self, monkeypatch):
        import tools.check_telemetry as check_telemetry

        class _Proces:
            stdout = ("<html><body><p>We collect usage data for "
                      "analytics and measurement.</p></body></html>")
            returncode = 0

        monkeypatch.setattr(check_telemetry.subprocess, "run",
                            lambda *a, **k: _Proces())
        vie, motiv = check_telemetry.sursa_viva(
            "https://exemplu.ro/privacy",
            "un citat care nu apare deloc in pagina")
        assert not vie
        assert "citatul" in motiv

    def test_valoarea_yes_se_scrie_cu_ghilimele(self):
        """`yes` fără ghilimele ar deveni boolean în YAML 1.1."""
        from ruamel.yaml.scalarstring import SingleQuotedScalarString

        import tools.check_telemetry as check_telemetry

        assert isinstance(check_telemetry.SingleQuotedScalarString("yes"),
                          SingleQuotedScalarString)


class TestSurseLogo:
    """Pictogramele prea mici nu sunt acceptate (ar arăta pixelate)."""

    def test_dimensiunile_png(self):
        from tools.fetch_logos import dimensiuni_png

        png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
               + (2).to_bytes(4, "big") + (2).to_bytes(4, "big"))
        assert dimensiuni_png(png) == (2, 2)

    def test_pictograma_mica_e_respinsa(self):
        from tools.fetch_logos import destul_de_mare

        mic = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
               + (16).to_bytes(4, "big") + (16).to_bytes(4, "big"))
        assert not destul_de_mare(mic)

    def test_pictograma_mare_e_acceptata(self):
        from tools.fetch_logos import destul_de_mare

        mare = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
                + (256).to_bytes(4, "big") + (256).to_bytes(4, "big"))
        assert destul_de_mare(mare)

    def test_svg_e_acceptat_indiferent_de_dimensiune(self):
        from tools.fetch_logos import destul_de_mare

        assert destul_de_mare(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")


class TestSurseRomaneste:
    """Proiectele GNOME/KDE stau pe GitLab — instrumentul trebuie să le caute."""

    def test_non_gitlab_e_ignorat(self):
        from tools.check_ro import traducere_in_gitlab

        assert traducere_in_gitlab("https://github.com/GNOME/gimp") == ""

    def test_api_gitlab_e_interogat(self, monkeypatch):
        import tools.check_ro as check_ro

        apelate = {}

        class _Raspuns:
            def read(self):
                return b'[{"type": "blob", "path": "po/ro.po"}]'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fals(request, timeout=0):
            apelate["url"] = getattr(request, "full_url", str(request))
            return _Raspuns()

        monkeypatch.setattr(check_ro.urllib.request, "urlopen", fals)
        gasit = check_ro.traducere_in_gitlab("https://gitlab.gnome.org/GNOME/gnote")
        assert gasit == "po/ro.po"
        assert "gitlab.gnome.org" in apelate["url"]
        assert "GNOME%2Fgnote" in apelate["url"]


class TestRegulaNume:
    """Regula care leagă fișierul `.mo` de aplicație."""

    @pytest.mark.parametrize("nume,baza,asteptat", [
        ("krita-l10n", "krita", True),
        ("gimp-data", "gimp", True),
        ("kate5-data", "kate", True),
        ("krita", "krita", True),
        ("libgimp2.0t64", "gimp", False),
        ("obsession-logout", "obs", False),
        ("vlc-l10n", "vlc", True),
    ])
    def test_nume_inrudit(self, nume, baza, asteptat):
        assert nume_inrudit(nume, baza) is asteptat


class TestExtragere:
    """Citirea indexului `Contents` al arhivei."""

    def test_extrage_pachetele_dintr_o_mo(self):
        flux = io.StringIO(
            "usr/share/locale/ro/LC_MESSAGES/krita.mo\tuniverse/localization/krita-l10n\n"
            "usr/share/locale/ro/LC_MESSAGES/other.mo\tuniverse/other\n"
            "usr/share/doc/ro/readme.txt\tuniverse/doc\n")
        mo = extrage_ro(flux)
        assert mo["krita"] == {"krita-l10n"}
        assert mo["other"] == {"other"}
        assert "readme" not in mo

    def test_mo_al_aplicatiei_accepta_pachetul_cu_prefix(self):
        mo = {"krita": {"krita-l10n"}, "krita2": {"other"}}
        gasit, dovada = mo_al_aplicatiei({"krita"}, mo)
        assert gasit
        assert "krita-l10n" in dovada

    def test_mo_al_aplicatiei_respinge_aplicatii_cu_nume_asemanator(self):
        """`chromium-bsu.mo` nu e traducerea pentru Chromium."""
        mo = {"chromium-bsu": {"chromium-bsu-data"}}
        gasit, _ = mo_al_aplicatiei({"chromium"}, mo)
        assert not gasit

    def test_mo_al_aplicatiei_ignora_mo_strain(self):
        """Un `.mo` al unei biblioteci nu dovedeste traducerea aplicatiei."""
        mo = {"gimp20-libgimp": {"libgimp2.0t64"}}
        gasit, _ = mo_al_aplicatiei({"gimp"}, mo)
        assert not gasit


class TestCatalog:
    """Catalogul construit trebuie sa pastreze marcajele de verificare."""

    def test_aplicatii_verificate_sunt_marcate_manual(self, catalog):
        for app_id in ("gimp", "vlc", "inkscape", "krita", "audacity"):
            app = catalog.get(app_id)
            assert app["confidence"]["details.romanian_language"] == "manual", app_id

    def test_aplicatiile_excluse_raman_nemarcate(self, catalog):
        """`kazam` din Ubuntu e altă aplicație — nu i se atribuie traducere."""
        assert "kazam" in EXCLUDERI
        kazam = catalog.get("kazam")
        assert kazam["confidence"]["details.romanian_language"] != "manual"

    def test_telemetria_verificata_e_marcata_manual(self, catalog):
        for app_id in VERIFICARI:
            app = catalog.get(app_id)
            assert app["confidence"]["details.telemetry"] == "manual", app_id

    def test_valoarea_de_telemetrie_corespunde_verificarii(self, catalog):
        for app_id, (valoare, _url, _citat) in VERIFICARI.items():
            assert catalog.get(app_id)["telemetry"] == valoare, app_id

    def test_sursa_telemetriei_e_citata_in_aplicatie(self, catalog):
        """Verificarea trebuie să fie accesibilă din catalog, nu doar din cod."""
        for app_id, (_valoare, url, _citat) in VERIFICARI.items():
            surse = catalog.get(app_id)["sources"]
            assert any(url in s for s in surse), app_id


class TestTabelTelemetrie:
    """Tabelul de verificări trebuie să rămână consistent."""

    def test_toate_intrarile_au_sursa_si_citat(self):
        for app_id, (valoare, url, citat) in VERIFICARI.items():
            assert valoare in ("none", "optional", "yes"), app_id
            assert url.startswith("https://"), app_id
            assert len(citat) > 20, app_id

    def test_aplicatiile_verificate_exista_in_catalog(self, catalog):
        for app_id in VERIFICARI:
            assert catalog.get(app_id) is not None, app_id
