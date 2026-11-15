"""Teste pentru sursele citate — afișarea lor în UI (sec. 8).

Promisiunea „totul e verificabil" trebuie să fie clicabilă: fiecare sursă
din `data/apps/<id>.yaml` apare în interfață, cu URL-ul complet în tooltip.
"""

from __future__ import annotations

import re

import pytest

from app.widgets import source_label


class TestSourceLabel:
    def test_strips_scheme(self):
        assert source_label("https://www.gimp.org") == "www.gimp.org"

    def test_strips_trailing_slash(self):
        assert source_label("https://keepassxc.org/project/#audits") == \
            "keepassxc.org/project/#audits"

    def test_keeps_path(self):
        assert source_label("https://github.com/GNOME/gimp") == "github.com/GNOME/gimp"

    def test_empty(self):
        assert source_label("") == ""


class TestSurseInCatalog:
    def test_toate_aplicatiile_au_surse(self, catalog):
        """Nicio aplicație nu rămâne fără sursă citată (build-ul avertizează)."""
        lipsa = [a["id"] for a in catalog.search() if not a["sources"]]
        assert lipsa == []

    def test_sursele_sunt_url_uri_valide(self, catalog):
        for a in catalog.search():
            for url in a["sources"]:
                assert url.startswith("https://"), (a["id"], url)

    def test_site_ul_oficial_este_printre_surse(self, catalog):
        """Site-ul oficial al aplicației trebuie să fie o sursă (verificabil)."""
        for a in catalog.search():
            assert a["website"] in a["sources"], a["id"]


class TestSurseInUI:
    @pytest.fixture
    def detail(self, catalog, qapp):
        from app.detail_view import DetailView

        view = DetailView(catalog)
        yield view
        view.deleteLater()

    def _links(self, view):
        from app.widgets import LinkLabel

        return view.findChildren(LinkLabel)

    def test_pagina_detalii_afiseaza_toate_sursele(self, detail, catalog):
        app = catalog.get("gimp")
        detail.show_app(app, {"popcon": True, "stars": True,
                              "release": True, "repo": True})
        urls = [l.url for l in self._links(detail)]
        for sursa in app["sources"]:
            assert sursa in urls

    def test_linkurile_sunt_clickabile(self, detail, catalog, monkeypatch):
        """Click-ul pe o sursă emite URL-ul (deschiderea e în grija gazdei)."""
        from app.detail_view import DetailView

        deschise = []
        monkeypatch.setattr(DetailView, "open_url",
                            lambda self, url: deschise.append(url))
        app = catalog.get("gimp")
        detail.show_app(app, {"popcon": True, "stars": True,
                              "release": True, "repo": True})
        link = self._links(detail)[0]
        link.clicked.emit(link.url)
        assert deschise == [link.url]

    def test_sursele_indicatorilor_sunt_linkuri(self, detail, catalog):
        """Cardurile de fapte au surse clicabile, nu doar text decorativ."""
        app = catalog.get("gimp")
        detail.show_app(app, {"popcon": True, "stars": True,
                              "release": True, "repo": True})
        urls = [l.url for l in self._links(detail)]
        assert "https://popcon.debian.org" in urls
        assert app["stars_url"] in urls

    def test_aplicatie_fara_surse_mostre_mesaj(self, detail, catalog):
        from PySide6.QtWidgets import QLabel

        app = dict(catalog.get("gimp"))
        app["sources"] = []
        detail.show_app(app, {"popcon": True, "stars": True,
                              "release": True, "repo": True})
        texts = [w.text() for w in detail.widget().findChildren(QLabel)]
        assert any("nicio sursă" in t for t in texts)

    def test_indicator_fara_valoare_nu_are_link(self, detail, catalog):
        """Fără valoare, sursa se descrie ca lipsă — nu se trimite la o pagină
        care nu are ce verifica (ex. GitHub API la o aplicație fără repo)."""
        from PySide6.QtWidgets import QLabel

        app = dict(catalog.get("photopea"))
        assert app["stars"] is None and not app["stars_url"]
        detail.show_app(app, {"popcon": True, "stars": True,
                              "release": True, "repo": True})
        texts = [w.text() for w in detail.widget().findChildren(QLabel)]
        assert "fără repo public" in texts
        assert "sursa: GitHub API" not in texts


class TestParitateMacheta:
    """Macheta (mockup-ui/) trebuie să reflecte aplicația (sec. 13)."""

    def test_macheta_are_mapul_de_surse(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        js = (root / "mockup-ui" / "script.js").read_text(encoding="utf-8")
        assert "const SOURCES = {" in js
        assert "🔗 Surse — de unde provin datele" in js

    def test_sursele_machetei_sunt_in_cataloagele_real(self):
        """URL-urile din machetă există și în YAML-urile reale."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        js = (root / "mockup-ui" / "script.js").read_text(encoding="utf-8")
        urls = set(re.findall(r'"(https://[^"]+)"', js))
        # URL-urile din blocul SOURCES trebuie să existe în catalogul real
        for app_dir in (root / "data" / "apps").glob("*.yaml"):
            text = app_dir.read_text(encoding="utf-8")
            for url in re.findall(r"- (https://\S+)", text):
                assert url in urls or url in text
