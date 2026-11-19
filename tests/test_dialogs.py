"""Teste pentru dialogul de Setări (scroll, atributul lipsă, butonul de refresh).

Trei bug-uri raportate de utilizator, cu capturi:
1. rândurile de jos ale dialogului erau tăiate (fără scrollbar);
2. „Actualizează catalogul acum" arunca „object has no attribute 'catalog'";
3. butoanele APT/Snap/Flatpak deveneau albe la hover, cu text invizibil.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton, QScrollArea


def _setari(tmp_path) -> QSettings:
    """Setări izolate (QSettings în fișier temporar)."""
    return QSettings(str(Path(tmp_path) / "test.ini"), QSettings.IniFormat)


@pytest.fixture
def setari(tmp_path):
    """Setări izolate (QSettings în fișier temporar)."""
    return _setari(tmp_path)


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

    def test_propunerea_ai_are_nevoie_de_catalog(self, dialog):
        """„Propune o aplicație cu AI…" folosește tot `self.catalog`."""
        assert dialog.catalog is not None
        assert hasattr(dialog.catalog, "db_path")


class TestActualizareCatalog:
    """„Actualizează catalogul acum” trebuie să meargă într-o instalare de sistem.

    Raportat de utilizator: în pachetul instalat (`/opt/alterna/_internal/`)
    butonul arunca „[Errno 13] Permission denied: …/catalog-nou.db” — catalogul
    aplicației e într-un director de sistem, read-only pentru utilizator.
    """

    @staticmethod
    def _asteapta(dialog, qapp, semn="✓", treceri=200):
        for _ in range(treceri):
            qapp.processEvents()
            if semn in dialog.update_status.text():
                return dialog.update_status.text()
            qapp.processEvents()
        return dialog.update_status.text()

    def test_descarcarea_merge_in_directorul_utilizatorului(
            self, dialog, catalog, monkeypatch, tmp_path, qapp):
        """Ținta descărcării e directorul de date, nu directorul aplicației."""
        from app import catalog_update

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        captat = {}

        def fake_download(dest_dir, timeout=60, filename=None):
            captat["dest"] = Path(dest_dir)
            return Path(dest_dir) / "catalog.db"

        monkeypatch.setattr(catalog_update, "download_catalog", fake_download)
        dialog.update_btn.click()
        # așteptăm thread-ul (callback-ul rulează în thread-ul UI)
        for _ in range(200):
            qapp.processEvents()
            if "dest" in captat:
                break
            qapp.processEvents()
        assert captat.get("dest") == tmp_path / "xdg" / "Alterna", (
            f"descărcarea a mers în {captat.get('dest')}, nu în directorul "
            f"de date al utilizatorului")

    def test_instalare_de_sistem_scrie_in_directorul_utilizatorului(
            self, catalog, tmp_path, monkeypatch, qapp):
        """Cu un catalog de sistem read-only, actualizarea merge la utilizator."""
        import os
        import shutil

        if os.geteuid() == 0:
            pytest.skip("rulând ca root, permisiunile nu se aplică")

        from app import catalog_update
        from app.db import Catalog

        sistem = tmp_path / "opt" / "alterna" / "_internal"
        sistem.mkdir(parents=True)
        catalog_sistem = sistem / "catalog.db"
        shutil.copy2(catalog.db_path, catalog_sistem)
        os.chmod(sistem, 0o555)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

        descarcat = tmp_path / "descarcare" / "catalog.db"
        descarcat.parent.mkdir(parents=True)
        shutil.copy2(catalog.db_path, descarcat)

        utilizator = tmp_path / "xdg" / "Alterna" / "catalog.db"
        final, backup = catalog_update.install_catalog(
            descarcat, catalog_sistem, utilizator)
        os.chmod(sistem, 0o755)

        assert final == utilizator, "actualizarea trebuie să ajungă la utilizator"
        assert backup is None, "nu înlocuim nimic în directorul de sistem"
        assert utilizator.exists()
        assert Catalog(utilizator).app_count == catalog.app_count

    def test_mesajul_nu_are_eroare_tehnica(self, catalog, tmp_path, monkeypatch,
                                            qapp):
        """Utilizatorul nu trebuie să vadă „[Errno 13] Permission denied”."""
        import os

        if os.geteuid() == 0:
            pytest.skip("rulând ca root, permisiunile nu se aplică")

        from app import catalog_update
        from app.db import Catalog
        from app.dialogs import SettingsDialog

        sistem = tmp_path / "opt" / "_internal"
        sistem.mkdir(parents=True)
        catalog_sistem = sistem / "catalog.db"
        shutil.copy2(catalog.db_path, catalog_sistem)
        os.chmod(sistem, 0o555)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

        cat = Catalog(catalog_sistem)
        dialog = SettingsDialog(_setari(tmp_path), cat)
        descarcat = tmp_path / "descarcare" / "catalog.db"
        descarcat.parent.mkdir(parents=True)
        shutil.copy2(catalog.db_path, descarcat)

        def fake_download(dest_dir, timeout=60, filename=None):
            return descarcat

        monkeypatch.setattr(catalog_update, "download_catalog", fake_download)
        dialog.update_btn.click()
        mesaj = self._asteapta(dialog, qapp, "✓")
        os.chmod(sistem, 0o755)
        cat.close()
        dialog.close()

        assert "Errno" not in mesaj and "Permission denied" not in mesaj, (
            f"mesajul conține o eroare tehnică: {mesaj!r}")
        assert "utilizatorul tău" in mesaj, (
            f"mesajul nu spune că actualizarea s-a aplicat local: {mesaj!r}")

    def test_eroarea_de_retea_e_prietenenoasa(self, dialog, catalog,
                                              monkeypatch, qapp):
        """Eroarea de rețea se arată ca mesaj, nu ca excepție tehnică."""
        from app import catalog_update

        def fake_download(dest_dir, timeout=60, filename=None):
            raise catalog_update.UpdateError("catalog de test — fără rețea")

        monkeypatch.setattr(catalog_update, "download_catalog", fake_download)
        dialog.update_btn.click()
        mesaj = self._asteapta(dialog, qapp, "✗")
        assert "✗" in mesaj, f"statusul nu arată eroarea: {mesaj!r}"
        assert "attribute" not in mesaj.lower(), (
            "AttributeError — atributul `catalog` lipsește din dialog")
        assert "catalog de test" in mesaj


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


class TestModelIncarcatOllama:
    """Câmpul „Model” trebuie să arate modelul încărcat în Ollama.

    Utilizatorul își alege modelul în Ollama; aplicația nu trebuie să impună
    unul implicit (llama3.1), ci pe cel pe care l-a încărcat el.
    """

    @staticmethod
    def _asteapta(dialog, qapp, semn, treceri=300):
        for _ in range(treceri):
            qapp.processEvents()
            if semn in dialog.ai_status.text():
                return dialog.ai_status.text()
            qapp.processEvents()
        return dialog.ai_status.text()

    def test_campul_model_se_completeaza_cu_modelul_incarcat(
            self, dialog, qapp, monkeypatch):
        from app.ai import OllamaClient

        monkeypatch.setattr(OllamaClient, "loaded_models",
                            lambda self, timeout=5: ["qwen3:8b"])
        dialog.ai_combo.setCurrentIndex(1)  # „Model local (Ollama)”
        status = self._asteapta(dialog, qapp, "qwen3:8b")
        assert "qwen3:8b" in status, status
        assert dialog.ai_ollama_model.text() == "qwen3:8b", (
            f"câmpul Model arată {dialog.ai_ollama_model.text()!r}")

    def test_alegerea_manuala_nu_e_suprascrisa(
            self, dialog, qapp, monkeypatch):
        """Dacă utilizatorul scrie alt model, îl respectăm."""
        from app.ai import OllamaClient

        monkeypatch.setattr(OllamaClient, "loaded_models",
                            lambda self, timeout=5: ["qwen3:8b"])
        dialog.ai_ollama_model.setText("llama3.1:8b")
        dialog.ai_combo.setCurrentIndex(1)
        self._asteapta(dialog, qapp, "qwen3:8b")
        assert dialog.ai_ollama_model.text() == "llama3.1:8b", (
            "alegerea manuală a fost suprascrisă")

    def test_fara_model_incarcat_se_explica(self, dialog, qapp, monkeypatch):
        from app.ai import OllamaClient

        monkeypatch.setattr(OllamaClient, "loaded_models",
                            lambda self, timeout=5: [])
        dialog.ai_combo.setCurrentIndex(1)
        status = self._asteapta(dialog, qapp, "Nu e niciun model")
        assert "Nu e niciun model încărcat" in status, status


class TestLmStudio:
    """Sursa „Model local (LM Studio)” — modelul încărcat apare în câmp."""

    @staticmethod
    def _asteapta(dialog, qapp, semn, treceri=300):
        for _ in range(treceri):
            qapp.processEvents()
            if semn in dialog.ai_status.text():
                return dialog.ai_status.text()
            qapp.processEvents()
        return dialog.ai_status.text()

    def test_sursa_lmstudio_exista(self, dialog):
        from app.dialogs import AI_SOURCES

        assert dialog.ai_combo.count() == 4
        assert dict(AI_SOURCES)["lmstudio"] == "Model local (LM Studio)"

    def test_campul_model_arata_modelul_incarcat_in_lmstudio(
            self, dialog, qapp, monkeypatch):
        from app.ai import LmStudioClient

        monkeypatch.setattr(LmStudioClient, "loaded_models",
                            lambda self, timeout=5: ["qwen/qwen3-8b"])
        dialog.ai_combo.setCurrentIndex(2)  # „Model local (LM Studio)”
        status = self._asteapta(dialog, qapp, "qwen/qwen3-8b")
        assert "qwen/qwen3-8b" in status, status
        assert dialog.ai_ollama_model.text() == "qwen/qwen3-8b", (
            f"câmpul Model arată {dialog.ai_ollama_model.text()!r}")

    def test_alegerea_manuala_nu_e_suprascrisa(self, dialog, qapp, monkeypatch):
        from app.ai import LmStudioClient

        monkeypatch.setattr(LmStudioClient, "loaded_models",
                            lambda self, timeout=5: ["qwen/qwen3-8b"])
        dialog.ai_ollama_model.setText("qwen2.5-coder-3b-instruct")
        dialog.ai_combo.setCurrentIndex(2)
        self._asteapta(dialog, qapp, "qwen/qwen3-8b")
        assert dialog.ai_ollama_model.text() == "qwen2.5-coder-3b-instruct", (
            "alegerea manuală a fost suprascrisă")

    def test_clientul_lmstudio_citeste_modelele_incarcate(self):
        """`loaded_instances` = model încărcat; `/v1/models` nu distinge."""
        from unittest.mock import patch

        from app.ai import LmStudioClient

        with patch.object(
            LmStudioClient,
            "_get_json",
            return_value={
                "models": [
                    {"key": "qwen/qwen3-8b", "loaded_instances": [{"id": "x"}]},
                    {"key": "qwen2.5-coder-3b-instruct", "loaded_instances": []},
                ]
            },
        ):
            modele = LmStudioClient().loaded_models()
        assert modele == ["qwen/qwen3-8b"], modele
