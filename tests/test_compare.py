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

    def test_evidentiere_verde(self, catalog, apps_security):
        rows = comparison_rows(apps_security, catalog.taxonomy("security"))
        by_label = {r[0]: r for r in rows}
        # Licență: keepassxc + bitwarden sunt FOSS (index 0, 1)
        assert by_label["Licență"][2]["best"] == {0, 1}
        # Preț: 1password e plătit
        assert by_label["Preț"][2]["best"] == {0, 1}
        # Dimensiune: keepassxc (50 MB) e cea mai mică
        assert by_label["Dimensiune la instalare"][2]["best"] == {0}
        # Telemetrie: doar keepassxc fără
        assert by_label["Telemetrie"][2]["best"] == {0}
        # Matrice: „ssh_agent" — doar keepassxc are „free"
        assert by_label["Agent SSH integrat (gestionare chei SSH)"][2]["best"] == {0}


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
