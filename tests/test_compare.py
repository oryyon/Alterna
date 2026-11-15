"""Teste pentru app/compare_view.py — tabelul de comparație + export (sec. 14, 15)."""

from __future__ import annotations

import json

import pytest

from app.compare_view import EXPORT_FORMATS, comparison_rows, export_content


@pytest.fixture
def apps_security(catalog):
    return [catalog.get(i) for i in ("keepassxc", "bitwarden", "1password")]


@pytest.fixture
def apps_mixte(catalog):
    return [catalog.get(i) for i in ("gimp", "vlc")]


class TestRanduri:
    def test_14_criterii_fara_taxonomie(self, catalog, apps_mixte):
        rows = comparison_rows(apps_mixte, catalog.taxonomy("graphics"))
        labels = [r[0] for r in rows]
        assert len(rows) == 14
        assert labels[0] == "Descriere" and labels[-1] == "Taguri"
        assert "FUNCȚIONALITĂȚI" not in labels  # fără taxonomie → fără matrice

    def test_matrice_doar_aceeasi_categorie_cu_taxonomie(self, catalog, apps_security):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"))
        labels = [r[0] for r in rows]
        assert labels.count("FUNCȚIONALITĂȚI") == 1
        assert len(rows) == 14 + 1 + 18

    def test_matrice_absenta_la_categorii_mixte(self, catalog):
        # Regula sec. 15: matricea NU apare dacă aplicațiile sunt din categorii diferite,
        # chiar dacă taxonomia e furnizată
        apps = [catalog.get("keepassxc"), catalog.get("bitwarden"), catalog.get("gimp")]
        rows = comparison_rows(apps, catalog.taxonomy("security"))
        assert all(r[0] != "FUNCȚIONALITĂȚI" for r in rows)

    def test_evidentiere_pe_criterii_verificate(self, catalog, apps_security):
        """Evidențierea (avantajul obiectiv) rămâne pe criteriile verificate."""
        rows = comparison_rows(apps_security, catalog.taxonomy("security"))
        by_label = {r[0]: r for r in rows}
        # Licență: keepassxc + bitwarden sunt FOSS (index 0, 1)
        assert by_label["Licență"][2]["best"] == {0, 1}
        # Preț: 1password e plătit
        assert by_label["Preț"][2]["best"] == {0, 1}
        # Matrice: „ssh_agent" — doar keepassxc are „free"
        assert by_label["Agent SSH integrat (gestionare chei SSH)"][2]["best"] == {0}

    def test_criterii_estimate_nu_sunt_evidentiate(self, catalog, apps_security):
        """Pe un criteriu estimat nu declarăm avantaj (review: „recomandată
        doar când este demonstrabilă"). Dimensiunea, telemetria și limba
        română sunt estimări editoriale → fără verde."""
        rows = comparison_rows(apps_security, catalog.taxonomy("security"))
        by_label = {r[0]: r for r in rows}
        for label in ("Dimensiune la instalare", "Telemetrie", "Limbă română"):
            assert by_label[label][2]["best"] == set(), label
            assert by_label[label][2]["neevidentiat"] == "estimated", label


class TestComparabilitate:
    """Dimensiunile se compară doar între ele, în aceeași distribuție."""

    def _app(self, size, basis="deb"):
        return {"install_size_mb": size, "size_basis": basis}

    def test_aplicatii_web_sunt_excluse(self):
        """O aplicație web nu se instalează local — nu are ce „câștiga"."""
        from app.compare_view import size_best_indexes

        apps = [self._app(0, "web"), self._app(50, "deb")]
        assert size_best_indexes(apps) == set()

    def test_comparare_doar_in_aceeasi_distributie(self):
        """Un .deb și un AppImage nu se raportează la același lucru."""
        from app.compare_view import size_best_indexes

        apps = [self._app(500, "appimage"), self._app(50, "deb")]
        # fiecare grup are un singur membru → niciun „cel mai mic"
        assert size_best_indexes(apps) == set()

    def test_cea_mai_mica_din_aceeasi_distributie(self):
        from app.compare_view import size_best_indexes

        apps = [self._app(300, "deb"), self._app(50, "deb"), self._app(900, "appimage")]
        assert size_best_indexes(apps) == {1}

    def test_grup_de_un_singur_membru(self):
        """Un singur candidat nu e „cel mai mic" din ceva — nu are cu cine."""
        from app.compare_view import size_best_indexes

        apps = [self._app(50, "deb")]
        assert size_best_indexes(apps) == set()

    def test_egalitate_la_minim(self):
        from app.compare_view import size_best_indexes

        apps = [self._app(50, "deb"), self._app(50, "deb")]
        assert size_best_indexes(apps) == {0, 1}


class TestMotivEvidentiere:
    """Fiecare avantaj evidențiat spune ȘI de ce (review: „explicație la
    fiecare highlight")."""

    def test_motiv_pentru_fiecare_rand_evidentiat(self):
        from app.compare_view import ROW_REASONS

        for rand in ("Licență", "Preț", "Platforme", "Ultima versiune"):
            assert rand in ROW_REASONS, rand
            assert len(ROW_REASONS[rand]) > 10, rand

    def test_legenda_spune_avantaj_obiectiv(self):
        from app.compare_view import CompareView

        assert CompareView is not None
        import inspect
        text = inspect.getsource(CompareView)
        assert "avantaj obiectiv" in text
        assert "cea mai bună valoare" not in text


class TestExportHonest:
    """Exportul poartă marcajul de certitudine — o comparație trimisă
    altcuva trebuie să fie la fel de onestă ca cea din aplicație."""

    def test_exportul_marcheaza_criteriile_estimate(self, catalog, apps_security):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"))
        md = export_content("md", apps_security, rows)
        assert "≈ Dimensiune la instalare" in md
        assert "≈ Telemetrie" in md

    def test_exportul_pastreaza_criteriile_verificate(self, catalog, apps_security):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"))
        md = export_content("md", apps_security, rows)
        assert "Licență" in md
        assert "≈ Licență" not in md


class TestExport:
    @pytest.mark.parametrize("fmt", list(EXPORT_FORMATS))
    def test_formate(self, catalog, apps_security, fmt):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"),
                               for_export=True)
        out = export_content(fmt, apps_security, rows)
        assert "KeePassXC" in out and "Bitwarden" in out and "1Password" in out

    def test_json_valid(self, catalog, apps_security):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"),
                               for_export=True)
        data = json.loads(export_content("json", apps_security, rows))
        assert data["aplicatii"] == ["KeePassXC", "Bitwarden", "1Password"]
        assert data["criterii"]["Licență"] == ["Open Source", "Open Source", "Comercial"]

    def test_markdown_structura(self, catalog, apps_security):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"),
                               for_export=True)
        md = export_content("md", apps_security, rows)
        assert md.startswith("# Comparație: KeePassXC vs Bitwarden vs 1Password")
        assert "| Criteriu | **KeePassXC** |" in md

    def test_csv_ghilimele(self, catalog):
        # descrierea cu virgule trebuie să rămână o singură celulă
        apps = [catalog.get("gimp"), catalog.get("vlc")]
        rows = comparison_rows(apps, [], for_export=True)
        csv = export_content("csv", apps, rows)
        assert csv.splitlines()[0] == '"Criteriu";"GIMP";"VLC"'
