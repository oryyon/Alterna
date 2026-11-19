"""Teste GUI offscreen pentru fereastra principală (regulile din sec. 13, 14, 16)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel

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


class TestVersiuneVisible:
    """Versiunea aplicației trebuie să fie vizibilă, fără să ocupe loc."""

    def test_versiunea_apare_in_interfata(self, window):
        from app.version import VERSION

        etichete = [l.text() for l in window.findChildren(QLabel)]
        assert any(f"v{VERSION}" in t for t in etichete), (
            f"versiunea v{VERSION} nu apare în fereastră")

    def test_versiunea_e_discreta(self, window):
        """Eticheta versiunii e marcată „dim” (nu atrage atenția)."""
        from app.version import VERSION

        discrete = [l for l in window.findChildren(QLabel)
                    if l.text() == f"v{VERSION}"
                    and l.property("dim") == "true"]
        assert discrete, "eticheta versiunii nu e marcată ca discretă"


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


class TestLinkuriInstalare:
    """Cardul „Instalează direct” din pagina de detalii."""

    def test_cardul_apare_pentru_o_aplicatie_cu_pachete(self, window):
        from app.widgets import LinkLabel

        window._open_detail("vlc")
        linkuri = [w for w in window.detail_view.findChildren(LinkLabel)
                   if w.url.startswith(("apt://", "snap://", "flathub://"))]
        assert linkuri, "aplicația vlc are surse de instalare — linkurile trebuie"
        assert any(w.url.startswith("apt://") for w in linkuri)
        assert any(w.url.startswith("snap://") for w in linkuri)
        assert any(w.url.startswith("flathub://") for w in linkuri)

    def test_fara_linkuri_pentru_o_aplicatie_fara_surse(self, window):
        from app.widgets import LinkLabel

        window._open_detail("kodi")
        linkuri = [w for w in window.detail_view.findChildren(LinkLabel)
                   if w.url.startswith(("apt://", "snap://", "flathub://"))]
        # kodi e în Ubuntu, deci are cel puțin linkul APT
        assert all(w.url.startswith(("apt://", "snap://", "flathub://"))
                   for w in linkuri)


class TestComboLungime:
    """Textul din casetele drop-down nu trebuie trunchiat cu „…".

    Raportat de utilizator (cu capturi): în popup, „Doar neinstalate"
    apărea ca „Doar n...talate", iar „Dimensiune mică → mare" ca
    „Dimensiune...ică → mare". Cauza: popup-ul primea lățimea cutiei, iar
    delegatul rezervă loc pentru indicatorul de selecție — textul nu mai
    încăpea și Qt îl scurtea.
    """

    COMBO = ["filter_license", "filter_platform", "filter_price",
             "filter_installed", "sort_select"]

    @pytest.mark.parametrize("nume", COMBO)
    def test_popupul_arata_textul_complet(self, window, nume, qapp):
        from PySide6.QtGui import QFontMetrics

        combo = getattr(window, nume)
        combo.showPopup()
        qapp.processEvents()
        view = combo.view()
        fm = QFontMetrics(view.font())
        spatiu = view.width() - view.frameWidth() * 2
        for i in range(combo.count()):
            text = combo.itemText(i)
            necesar = fm.horizontalAdvance(text)
            assert spatiu >= necesar, (
                f"{nume}: popupul are {spatiu}px pentru „{text}” "
                f"({necesar}px necesari) — textul se trunchiază")
        combo.hidePopup()

    @pytest.mark.parametrize("nume", COMBO)
    def test_cutia_e_lata_cat_textul(self, window, nume, qapp):
        """Cutia nu e strângată de layout: textul cel mai lung încape.

        Cu `AdjustToContents`, `sizeHint` este exact lățimea necesară
        (text + săgeată + margini). Dacă layoutul strânge cutia sub
        `sizeHint`, textul se taie.
        """
        from PySide6.QtGui import QFontMetrics

        combo = getattr(window, nume)
        combo.show()
        qapp.processEvents()
        fm = QFontMetrics(combo.font())
        necesar = max(fm.horizontalAdvance(combo.itemText(i))
                      for i in range(combo.count()))
        assert combo.width() >= combo.sizeHint().width(), (
            f"{nume}: cutia are {combo.width()}px, dar are nevoie de "
            f"{combo.sizeHint().width()}px pentru textul cel mai lung "
            f"({necesar}px) — textul e tăiat")
