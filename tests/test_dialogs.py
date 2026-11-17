"""Teste pentru dialogul de Setări (scroll, atributul lipsă, butonul de refresh).

Trei bug-uri raportate de utilizator, cu capturi:
1. rândurile de jos ale dialogului erau tăiate (fără scrollbar);
2. „Actualizează catalogul acum" arunca „object has no attribute 'catalog'";
3. butoanele APT/Snap/Flatpak deveneau albe la hover, cu text invizibil.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton, QScrollArea


@pytest.fixture
def setari(tmp_path):
    """Setări izolate (QSettings în fișier temporar)."""
    return QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat)


@pytest.fixture
def dialog(catalog, setari, qapp):
    from app.dialogs import SettingsDialog

    d = SettingsDialog(setari, catalog)
    yield d
    d.close()
    d.deleteLater()


class TestScroll:
    def test_contenutul_e_derulabil(self, dialog):
        """Dialogul are o zonă de derulare — rândurile de jos nu se taie."""
        assert isinstance(dialog.scroll, QScrollArea)
        assert dialog.scroll.widget() is not None
        assert dialog.scroll.widget().objectName() == "settingsContent"

    def test_butonul_inchide_e_inafarte_de_scroll(self, dialog):
        """„Închide" trebuie să rămână permanent vizibil, jos."""
        inchide = [b for b in dialog.findChildren(QPushButton)
                   if b.text() == "Închide"]
        assert inchide, "butonul „Închide\" lipsește"
        parinte_scroll = dialog.scroll.widget()
        assert inchide[0].parent() is not parinte_scroll, (
            "butonul „Închide\" e în zona derulantă — ar dispărea sub margine")

    def test_scrollbarul_apare_cand_contenutul_nu_incape(self, dialog, qapp):
        """La înălțime mică apare scrollbarul (conținutul e accesibil)."""
        dialog.resize(480, 320)
        dialog.show()
        qapp.processEvents()
        assert dialog.scroll.verticalScrollBar().maximum() > 0, (
            "conținutul e mai lung decât fereastra, dar nu apare scrollbar")


class TestCatalogAtribut:
    def test_dialogul_are_atributul_catalog(self, dialog, catalog):
        """Fără `self.catalog`, butonul de refresh arunca AttributeError."""
        assert dialog.catalog is catalog

    def test_refreshul_afiseaza_eroarea_de_retea_nu_attributeerror(
            self, dialog, catalog, monkeypatch, qapp):
        """Butonul de refresh trebuie să ajungă la eroul de rețea, nu la
        un AttributeError (regula: o excepție reală, mesaj real)."""
        from app import catalog_update

        def fake_download(dest_dir, timeout=60):
            raise catalog_update.UpdateError("catalog de test — fără rețea")

        monkeypatch.setattr(catalog_update, "download_catalog", fake_download)
        dialog.update_btn.click()
        for _ in range(100):
            qapp.processEvents()
            if "✗" in dialog.update_status.text():
                break
            qapp.processEvents()
        assert "✗" in dialog.update_status.text(), (
            f"statusul nu arată eroarea: {dialog.update_status.text()!r}")
        assert "attribute" not in dialog.update_status.text().lower(), (
            "AttributeError — atributul `catalog` lipsește din dialog")
        assert "catalog de test" in dialog.update_status.text()

    def test_propunerea_ai_are_nevoie_de_catalog(self, dialog):
        """„Propune o aplicație cu AI…" folosește tot `self.catalog`."""
        assert dialog.catalog is not None
        assert hasattr(dialog.catalog, "db_path")


def _luminozitate(culoare) -> float:
    """Luminanță relativă WCAG (0..1) dintr-o QColor."""
    canaluri = []
    for val in (culoare.redF(), culoare.greenF(), culoare.blueF()):
        canaluri.append(val / 12.92 if val <= 0.03928
                        else ((val + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canaluri[0] + 0.7152 * canaluri[1] + 0.0722 * canaluri[2]


def _contrast(c1, c2) -> float:
    """Raport de contrast WCAG între două culori."""
    l1, l2 = _luminozitate(c1), _luminozitate(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


class TestButoaneInstalare:
    """Butoanele APT/Snap/Flatpak: la hover textul trebuie să rămână vizibil.

    Raportat cu capturi: în toate temele, la hover fundalul devenea alb
    (culoarea textului temei) și textul rămânea tot alb → invizibil.
    """

    @pytest.mark.parametrize("tema", ["dark", "light", "ocean"])
    def test_textul_ramane_vizibil_la_hover(self, qapp, tema):
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QEnterEvent
        from app.theme import apply_theme
        from app.widgets import LinkLabel

        apply_theme(qapp, tema)
        buton = LinkLabel("APT", "apt://vlc")
        buton.setProperty("installLink", "true")
        buton.setProperty("link", "false")
        buton.resize(70, 26)
        buton.show()
        qapp.processEvents()
        # eveniment de intrare = starea :hover reală
        qapp.sendEvent(buton, QEnterEvent(QPoint(5, 5), QPoint(5, 5),
                                          QPoint(0, 0)))
        qapp.processEvents()

        imagine = buton.grab().toImage()
        frecvente = {}
        for x in range(imagine.width()):
            for y in range(imagine.height()):
                c = imagine.pixelColor(x, y)
                cheie = (c.red(), c.green(), c.blue())
                frecvente[cheie] = frecvente.get(cheie, 0) + 1
        # Fundalul = culoarea dominantă; textul = pixelul cu cel mai mare
        # contrast față de fundal (anti-aliasingul produce culori intermediare).
        fundal = max(frecvente, key=lambda c: frecvente[c])
        text = max(frecvente, key=lambda c: _contrast(QColor(*fundal),
                                                      QColor(*c)))
        raport = _contrast(QColor(*fundal), QColor(*text))
        assert raport >= 4.5, (
            f"tema {tema}: contrast text/fundal la hover = {raport:.1f}:1 "
            f"(sub 4.5:1) — text invizibil")

    def test_regula_qss_declara_culoarea_si_la_hover(self):
        """Regula QSS trebuie să declare `color` și în starea :hover.

        Fără `color` explicit, culoarea textului e moștenită de la regula
        QLabel[link="true"]:hover — care e chiar culoarea fundalului.
        """
        from app.theme import build_qss

        for tema in ("dark", "light", "ocean"):
            qss = build_qss(tema)
            linie = [l for l in qss.splitlines()
                     if 'QLabel[installLink="true"]:hover' in l]
            assert linie, f"tema {tema}: lipsește regula hover pentru instalare"
            assert "color:" in linie[0], (
                f"tema {tema}: regula hover nu declară `color` — "
                f"textul poate deveni invizibil")
