"""Teste GUI offscreen pentru fereastra principală (regulile din sec. 13, 14, 16)."""

from __future__ import annotations

import pytest

from app.main_window import MAX_COMPARE, MainWindow


@pytest.fixture
def window(qapp, catalog, tmp_path, monkeypatch):
    """Fereastra principală cu setări izolate (QSettings în fișier temporar)."""
    from PySide6.QtCore import QSettings
    monkeypatch.setattr(
        "app.main_window.QSettings",
        lambda *a: QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat))
    # `detecta=False`: detectarea instalării pornește un thread care ar
    # supraviețui fixture-ului (și ar face testele nedependente de sistem).
    w = MainWindow(catalog, detecta=False)
    yield w
    w.close()
    w.deleteLater()


class TestStructura:
    def test_categorii(self, window, catalog):
        # „Toate" + cele 13 categorii
        assert window.category_list.count() == 14
        assert window.catalog.app_count >= 100

    def test_titlu_initial(self, window):
        assert window.list_title.text() == "Aplicații populare"


class TestFiltreCautare:
    def test_cautare_actualizeaza_titlul_si_lista(self, window):
        window.search_edit.setText("parole")
        assert window.list_title.text() == "Căutare: „parole”"
        asteptat = len(window.catalog.search(text="parole"))
        assert window.result_count.text() == f"{asteptat} rezultate"
        assert asteptat > 0

    def test_categorie_selectata(self, window):
        row = [i for i, (s, _) in enumerate(window.catalog.categories)
               if s == "graphics"][0] + 1
        window.category_list.setCurrentRow(row)
        assert window.list_title.text() == "Grafică"
        asteptat = len(window.catalog.search(category="graphics"))
        assert window.result_count.text() == f"{asteptat} rezultate"

    def test_stare_goala(self, window):
        window.search_edit.setText("xyz-inexistent-123")
        assert "0 rezultate" in window.result_count.text()


class TestComparare:
    def test_buton_compara_doar_in_liste_filtrate(self, window):
        # fereastra nu e afișată în teste → verificăm cu isHidden, nu isVisible
        assert window.compare_btn.isHidden()  # „Toate" → ascuns (sec. 14)
        window.search_edit.setText("a")
        assert not window.compare_btn.isHidden()

    def test_mod_comparare_se_anuleaza_la_toate(self, window):
        row = [i for i, (s, _) in enumerate(window.catalog.categories)
               if s == "security"][0] + 1
        window.category_list.setCurrentRow(row)
        window.compare_btn.click()
        assert window.compare_mode
        window.category_list.setCurrentRow(0)  # înapoi la „Toate"
        assert not window.compare_mode

    def test_max_4_selectii(self, window):
        row = [i for i, (s, _) in enumerate(window.catalog.categories)
               if s == "security"][0] + 1
        window.category_list.setCurrentRow(row)
        window.compare_btn.click()
        for app_id in ("keepassxc", "bitwarden", "1password", "proton-pass", "pass"):
            window._toggle_select(app_id)
        assert len(window.selected) == MAX_COMPARE

    def test_buton_vezi_activ_de_la_2(self, window):
        row = [i for i, (s, _) in enumerate(window.catalog.categories)
               if s == "security"][0] + 1
        window.category_list.setCurrentRow(row)
        window.compare_btn.click()
        window._toggle_select("keepassxc")
        assert not window.open_compare_btn.isEnabled()
        window._toggle_select("bitwarden")
        assert window.open_compare_btn.isEnabled()

    def test_matrice_securitate_in_tabel(self, window):
        row = [i for i, (s, _) in enumerate(window.catalog.categories)
               if s == "security"][0] + 1
        window.category_list.setCurrentRow(row)
        window.compare_btn.click()
        window._toggle_select("keepassxc")
        window._toggle_select("bitwarden")
        window.open_compare_btn.click()
        assert window.stack.currentIndex() == 2
        assert any(r[0] == "FUNCȚIONALITĂȚI" for r in window.compare_view.rows)


class TestNavigare:
    def test_detalii_si_inapoi(self, window):
        window._open_detail("gimp")
        assert window.stack.currentIndex() == 1
        assert window.status.currentMessage() == "Detalii: GIMP"

    def test_detalii_inexistent(self, window):
        window._open_detail("nu-exista")
        assert window.stack.currentIndex() == 0
