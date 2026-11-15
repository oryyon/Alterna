"""Teste pentru marcajele de certitudine (sec. 8 din IDEI_PROIECT.md).

Promisiunea „totul e verificabil" cere mai mult decât surse citate: trebuie
spus și cât de mult se poate baza pe fiecare valoare. Sistemul are patru
niveluri (auto / manual / estimated / unknown), configurate în
`data/confidence.yaml` și afișate în interfață.
"""

from __future__ import annotations

import pytest
import yaml

from app.confidence import (CONFIDENCE_FIELDS, LEVELS, LEVEL_MARKS,
                             field_label, weakest)


class TestModel:
    def test_niveluri(self):
        assert LEVELS == ("auto", "manual", "estimated", "unknown")

    def test_fiecare_nivel_are_marcaj_propriu(self):
        """Marcajele trebuie să fie distincte — altfel nu se pot deosebi."""
        assert len(set(LEVEL_MARKS.values())) == len(LEVELS)

    def test_weakest_alege_nivelul_maib_slab(self):
        assert weakest(["manual", "manual"]) == "manual"
        assert weakest(["auto", "manual"]) == "manual"
        assert weakest(["manual", "estimated"]) == "estimated"
        assert weakest(["manual", "unknown"]) == "unknown"
        assert weakest(["auto", "estimated"]) == "estimated"

    def test_weakest_pentru_lista_goala(self):
        assert weakest([]) == "unknown"

    def test_etichete_pentru_toate_campurile(self):
        for field in CONFIDENCE_FIELDS:
            assert field_label(field), field


class TestConfiguratie:
    def _raw(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        return yaml.safe_load(
            (root / "data" / "confidence.yaml").read_text(encoding="utf-8"))

    def test_confidence_yaml_exista_si_e_valid(self):
        assert "defaults" in self._raw()

    def test_nivelurile_implicite_sunt_valide(self):
        for field, level in self._raw()["defaults"].items():
            assert level in LEVELS, (field, level)
            assert level != "unknown", field

    def test_indicatorii_sunt_automatizati(self):
        """Cei 4 indicatori sincronizați automat trebuie marcați «auto»."""
        defaults = self._raw()["defaults"]
        for field in ("indicators.popcon_rank", "indicators.stars",
                      "indicators.latest_release", "indicators.in_ubuntu_repos"):
            assert defaults[field] == "auto", field


class TestBuild:
    def test_marcajele_sunt_scrise_in_baza(self, catalog):
        app = catalog.get("gimp")
        assert app["confidence"], "marcajele nu sunt încărcate"
        assert set(app["confidence"]) == set(CONFIDENCE_FIELDS)

    def test_indicatorii_sunt_automatizati_in_baza(self, catalog):
        app = catalog.get("gimp")
        assert app["confidence"]["indicators.popcon_rank"] == "auto"
        assert app["confidence"]["indicators.stars"] == "auto"

    def test_valoare_lipsa_devine_unknown(self, catalog):
        """Fără repo GitHub, stelele nu pot fi verificate → unknown."""
        photopea = catalog.get("photopea")
        assert photopea["stars"] is None
        assert photopea["confidence"]["indicators.stars"] == "unknown"
        assert photopea["confidence"]["indicators.stars_url"] == "unknown"

    def test_detaliile_sunt_estimari_fara_verificare(self, catalog):
        """Dimensiunea e măsurată (vezi TestDimensiuniVerificate); limba
        română e verificată pentru aplicațiile confirmate (vezi
        `tests/test_verificari.py`), dar telemetria rămâne estimare editorială
        dacă nu are politică de confidențialitate verificată."""
        gimp = catalog.get("gimp")
        assert gimp["confidence"]["details.telemetry"] == "estimated"
        assert gimp["confidence"]["details.romanian_language"] == "manual"

    def test_identitatea_este_manuala(self, catalog):
        gimp = catalog.get("gimp")
        for field in ("license", "price", "website", "developer"):
            assert gimp["confidence"][field] == "manual", field

    def test_override_din_yaml_are_prioritate(self):
        """Override-ul per aplicație bate nivelul implicit din config."""
        from tools.build_catalog import resolve_confidence

        app = {"name": "X", "description": "d", "category": "c",
               "license": "foss", "price": "free", "developer": "dev",
               "website": "https://x.test", "platforms": ["linux"],
               "tags": ["t"], "alternatives": [], "popularity": 10,
               "details": {"install_size_mb": 1, "first_release_year": 2000,
                           "file_formats": ["f"], "telemetry": "none",
                           "romanian_language": True},
               "indicators": {"popcon_rank": 1, "stars": 2,
                              "stars_url": "https://gh.test/x",
                              "latest_release": "2026-01",
                              "in_ubuntu_repos": True},
               "confidence": {"details.romanian_language": "manual"}}
        defaults = {"details.romanian_language": "estimated",
                    "indicators.popcon_rank": "auto"}
        niveluri = dict(resolve_confidence(app, defaults))
        assert niveluri["details.romanian_language"] == "manual"
        assert niveluri["indicators.popcon_rank"] == "auto"

    def test_valoare_lipsa_bate_override(self):
        """Override-ul nu poate transforma o valoare absentă în verificată."""
        from tools.build_catalog import resolve_confidence

        app = {"name": "X", "description": "d", "category": "c",
               "license": "foss", "price": "free", "developer": "dev",
               "website": "https://x.test", "platforms": ["linux"],
               "tags": ["t"], "alternatives": [], "popularity": 10,
               "details": {"install_size_mb": 1, "first_release_year": 2000,
                           "file_formats": ["f"], "telemetry": "none",
                           "romanian_language": None},
               "indicators": {"popcon_rank": None, "stars": None,
                              "stars_url": None,
                              "latest_release": "2026-01",
                              "in_ubuntu_repos": True},
               "confidence": {"details.romanian_language": "manual",
                              "indicators.popcon_rank": "manual"}}
        niveluri = dict(resolve_confidence(app, {}))
        assert niveluri["details.romanian_language"] == "unknown"
        assert niveluri["indicators.popcon_rank"] == "unknown"


class TestValidareBuild:
    """Regulile de validare pentru marcajele declarate manual."""

    def _validate(self, tmp_path, confidence_block):
        from tools.build_catalog import Reporter, validate_app

        app = {"id": "x", "name": "X", "description": "d", "category": "graphics",
               "license": "foss", "price": "free", "developer": "dev",
               "website": "https://x.test", "platforms": ["linux"],
               "tags": ["t"], "alternatives": [], "sources": ["https://x.test"],
               "details": {"install_size_mb": 1, "first_release_year": 2000,
                           "file_formats": ["f"], "telemetry": "none",
                           "romanian_language": True},
               "indicators": {"popcon_rank": 1, "stars": 2,
                              "stars_url": "https://gh.test/x",
                              "latest_release": "2026-01",
                              "in_ubuntu_repos": True}}
        app.update(confidence_block)
        path = tmp_path / "x.yaml"
        path.write_text(yaml.safe_dump(app), encoding="utf-8")
        rep = Reporter()
        validate_app(path, app, {}, rep)
        return rep

    def test_nivel_invalid_este_eroare(self, tmp_path):
        rep = self._validate(tmp_path, {"confidence": {"license": "sigur"}})
        assert any("nivel invalid" in e for e in rep.errors)

    def test_camp_necunoscut_este_eroare(self, tmp_path):
        rep = self._validate(tmp_path, {"confidence": {"inventat": "manual"}})
        assert any("câmp necunoscut" in e for e in rep.errors)

    def test_unknown_nu_se_declara(self, tmp_path):
        rep = self._validate(tmp_path, {"confidence": {"license": "unknown"}})
        assert any("unknown" in e for e in rep.errors)

    def test_nivel_valid_este_acceptat(self, tmp_path):
        rep = self._validate(tmp_path, {"confidence": {"license": "manual"}})
        assert not any("confidence" in e for e in rep.errors)


class TestUI:
    @pytest.fixture
    def detail(self, catalog, qapp):
        from app.detail_view import DetailView

        view = DetailView(catalog)
        yield view
        view.deleteLater()

    def test_badge_pe_cardurile_de_fapt(self, detail, catalog):
        from app.confidence import ConfidenceBadge

        detail.show_app(catalog.get("gimp"), {"popcon": True, "stars": True,
                                              "release": True, "repo": True})
        badges = detail.findChildren(ConfidenceBadge)
        assert badges, "nu există marcaje de certitudine"
        assert "auto" in {b.level for b in badges}

    def test_panoul_de_certitudine_groupeaza_campurile(self, detail, catalog):
        from PySide6.QtWidgets import QLabel

        detail.show_app(catalog.get("gimp"), {"popcon": True, "stars": True,
                                              "release": True, "repo": True})
        texts = [w.text() for w in detail.widget().findChildren(QLabel)]
        assert any("Certitudine" in t for t in texts)
        assert any("estimat" in t for t in texts)

    def test_nivelul_randului_e_cei_mai_slab(self):
        from app.compare_view import row_confidence

        apps = [
            {"confidence": {"details.telemetry": "manual"}},
            {"confidence": {"details.telemetry": "estimated"}},
        ]
        assert row_confidence("details.telemetry", apps) == "estimated"

    def test_rand_fara_camp_este_estimat(self):
        from app.compare_view import row_confidence

        assert row_confidence("", [{"confidence": {}}]) == "estimated"

    def test_marcaj_in_prima_coloana_a_tabelului(self, catalog, qapp):
        """Tabelul de comparație marchează fiecare rând cu nivelul lui."""
        from app.compare_view import CompareView

        view = CompareView()
        apps = [catalog.get(i) for i in ("keepassxc", "bitwarden")]
        view.show_comparison(apps, catalog.taxonomy("security"))
        table = view.findChild(__import__("PySide6.QtWidgets",
                                          fromlist=["QTableWidget"]).QTableWidget)
        assert table is not None
        antet = [table.item(r, 0).text() for r in range(1, table.rowCount())]
        marcate = [t for t in antet if t and t[0] in "⟳✓≈?"]
        assert marcate, "niciun rând nu e marcat cu nivelul de certitudine"


class TestDimensiuniVerificate:
    """Dimensiunea la instalare e măsurată, nu estimată (pachet + dependențe)."""

    def test_dimensiunile_verificate_sunt_marcate_auto(self, catalog):
        """Aplicațiile cu pachet Ubuntu au dimensiunea verificată automat."""
        gimp = catalog.get("gimp")
        assert gimp["confidence"]["details.install_size_mb"] == "auto"
        assert gimp["install_size_mb"] > 0

    def test_aplicatii_fara_pachet_isi_pastreaza_estimarea(self, catalog):
        """Fără pachet Ubuntu nu se inventează o dimensiune."""
        chrome = catalog.get("chrome")
        assert chrome["confidence"]["details.install_size_mb"] != "auto"

    def test_coliziune_de_nume_nu_trec_negresit(self, catalog):
        """„notion” în Ubuntu e un window manager, nu aplicația Notion —
        deci nu i se atribuie o dimensiune măsurată."""
        notion = catalog.get("notion")
        assert notion["confidence"]["details.install_size_mb"] != "auto"

    def test_randul_de_dimensiune_este_evidentiat_doar_daca_e_verificat(self, catalog):
        """Regula „avantaj obiectiv": verde doar pe criterii verificate."""
        from app.compare_view import comparison_rows

        gimp = catalog.get("gimp")
        vlc = catalog.get("vlc")
        rows = comparison_rows([gimp, vlc], [])
        by_label = {r[0]: r for r in rows}
        # ambele au dimensiune verificată → rândul e verificat → se evidențiază
        assert by_label["Dimensiune la instalare"][2]["best"], \
            "două dimensiuni verificate ar trebui evidențiate"
