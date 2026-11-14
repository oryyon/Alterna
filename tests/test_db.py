"""Teste pentru app/db.py — interogări, filtre, sortări (sec. 6, 16)."""

from __future__ import annotations


class TestSearch:
    def test_total(self, catalog):
        assert len(catalog.search()) == 100

    def test_filtru_categorie(self, catalog):
        rez = catalog.search(category="security")
        assert len(rez) == 6
        assert all(a["category"] == "security" for a in rez)

    def test_filtru_licenta_platforma_pret(self, catalog):
        rez = catalog.search(license_="foss", platform="linux", price="free")
        assert rez
        for a in rez:
            assert a["license"] == "foss"
            assert "linux" in a["platforms"]
            assert a["price"] == "free"

    def test_cautare_text(self, catalog):
        ids = {a["id"] for a in catalog.search(text="parole")}
        assert {"keepassxc", "bitwarden", "1password"} <= ids

    def test_cautare_dupa_tag(self, catalog):
        ids = {a["id"] for a in catalog.search(text="arhivare")}
        assert {"sevenzip", "peazip"} <= ids

    def test_cautare_fara_rezultat(self, catalog):
        assert catalog.search(text="xyz-inexistent-123") == []


class TestSortare:
    def test_implicita_e_ordinea_editoriala(self, catalog):
        ids = [a["id"] for a in catalog.search()[:5]]
        assert ids == ["firefox", "chrome", "vlc", "gimp", "libreoffice"]

    def test_az_za(self, catalog):
        az = [a["name"] for a in catalog.search(sort="az")]
        za = [a["name"] for a in catalog.search(sort="za")]
        assert az == sorted(az, key=str.lower)
        assert za == sorted(az, key=str.lower, reverse=True)

    def test_recent(self, catalog):
        rel = [a["latest_release"] for a in catalog.search(sort="recent")]
        assert rel == sorted(rel, reverse=True)

    def test_dimensiune_null_la_final(self, catalog):
        rez = catalog.search(sort="mic")
        sizes = [a["install_size_mb"] for a in rez]
        fara_null = [s for s in sizes if s is not None]
        assert fara_null == sorted(fara_null)
        assert all(s is None for s in sizes[len(fara_null):])


class TestHidratare:
    def test_get_complet(self, catalog):
        g = catalog.get("gimp")
        assert g["category_name"] == "Grafică"
        assert set(g["alternatives"]) == {"krita", "photopea", "photoshop"}
        assert g["platforms"] and g["tags"] and g["sources"]
        assert g["editors_choice"] == 1

    def test_get_inexistent(self, catalog):
        assert catalog.get("nu-exista") is None

    def test_features_security(self, catalog):
        k = catalog.get("keepassxc")
        assert k["features"]["chei_hardware"]["value"] == "partial"
        assert "YubiKey" in k["features"]["chei_hardware"]["note"]
        assert k["features"]["ssh_agent"]["value"] == "free"

    def test_taxonomie(self, catalog):
        tax = catalog.taxonomy("security")
        assert len(tax) == 18
        assert tax[0][0] == "offline"
        assert catalog.taxonomy("graphics") == []
