"""Teste pentru app/db.py — interogări, filtre, sortări (sec. 6, 16)."""

from __future__ import annotations


class TestSearch:
    def test_total(self, catalog):
        """Numărul vine din catalog — nu e înghețat în test."""
        assert len(catalog.search()) == catalog.app_count
        assert catalog.app_count >= 100

    def test_filtru_categorie(self, catalog):
        rez = catalog.search(category="security")
        toate = [a for a in catalog.search() if a["category"] == "security"]
        assert len(rez) == len(toate)
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
        """Implicit = popularitate descrescătoare, fără goluri la început."""
        primele = catalog.search()[:5]
        popularitati = [a["popularity"] for a in primele]
        # convenția proiectului: număr mai mic = mai popular (implicit, crescător)
        assert popularitati == sorted(popularitati)
        assert all(p is not None for p in popularitati)

    def test_az_za(self, catalog):
        az = [a["name"] for a in catalog.search(sort="az")]
        za = [a["name"] for a in catalog.search(sort="za")]
        assert az == sorted(az, key=str.lower)
        assert za == sorted(az, key=str.lower, reverse=True)

    def test_recent(self, catalog):
        """Cele cu data necunoscută stau la final, nu la început."""
        rel = [a["latest_release"] for a in catalog.search(sort="recent")]
        cunoscute = [r for r in rel if r is not None]
        assert cunoscute == sorted(cunoscute, reverse=True)
        if None in rel:
            # cele fără dată stau la final, după cele cu dată
            assert rel.index(None) == len(cunoscute)

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
        # lista e simetrică și poate avea mai multe elemente; verificăm
        # relațiile care contează, nu un set înghețat
        assert {"krita", "photopea", "photoshop"} <= set(g["alternatives"])
        assert g["id"] not in g["alternatives"]
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
        # toate categoriile au taxonomie (matricea de comparație, sec. 15)
        grafica = catalog.taxonomy("graphics")
        assert grafica, "categoria „Grafică” trebuie să aibă taxonomie"
        assert grafica[0][0] == "raster_editare"


class TestMatriceComparatie:
    """Matricea de funcționalități (sec. 15): toate categoriile au taxonomie.

    Taxonomia e cea care face comparația utilă: aceleași rânduri pentru toate
    aplicațiile din categorie, cu valori din vocabularul fix.
    """

    VALORI = {"free", "paid", "partial", "no", "unknown"}

    @staticmethod
    def _taxonomii():
        from pathlib import Path

        from ruamel.yaml import YAML

        yaml = YAML()
        baza = Path(__file__).resolve().parent.parent / "data" / "taxonomy"
        rezultat = {}
        for cale in sorted(baza.glob("*.yaml")):
            date = yaml.load(cale.read_text(encoding="utf-8"))
            rezultat[date["category"]] = list((date.get("features") or {}))
        return rezultat

    def test_fiecare_categorie_are_taxonomie(self, catalog):
        categorii = {a["category"] for a in catalog.search()}
        taxo = self._taxonomii()
        lipsa = sorted(categorii - set(taxo))
        assert not lipsa, f"categorii fără taxonomie: {lipsa}"
        assert len(taxo) >= 13, f"doar {len(taxo)} taxonomii"

    def test_fiecare_aplicatie_are_chei_din_taxonomie(self, catalog):
        taxo = self._taxonomii()
        greseli = []
        for app in catalog.search():
            chei = (app.get("features") or {}).keys()
            permise = set(taxo.get(app["category"], []))
            for cheie in chei:
                if cheie not in permise:
                    greseli.append(f"{app['id']}.{cheie}")
        assert not greseli, f"chei necunoscute: {greseli[:5]}"

    def test_valorile_sunt_din_vocabularul_fix(self, catalog):
        greseli = []
        for app in catalog.search():
            for cheie, valoare in (app.get("features") or {}).items():
                if valoare["value"] not in self.VALORI:
                    greseli.append(f"{app['id']}.{cheie}={valoare['value']}")
        assert not greseli, f"valori invalide: {greseli[:5]}"

    def test_matricea_are_randuri_pentru_toate_categoriile(self, catalog):
        """Fiecare categorie cu taxonomie are cel puțin 8 rânduri."""
        prea_putine = []
        for categorie in self._taxonomii():
            if len(catalog.taxonomy(categorie)) < 8:
                prea_putine.append(categorie)
        assert not prea_putine, f"taxonomii prea scurte: {prea_putine}"
