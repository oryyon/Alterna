"""Teste pentru detectarea aplicațiilor deja instalate (punctul 16).

Modulul `app/installed.py` interoghează sistemul de pachete, deci testele
**nu depind de mașina pe care rulează**: fiecare sursă primește un „alergator"
false, cu ieșirea captată. Ce se verifică aici e logica, nu sistemul:

- parsarea ieșirilor comenzilor (dpkg-query, snap list, flatpak list);
- asocierea dintre pachet și aplicația din catalog;
- faptul că o sursă indisponibilă înseamnă „necunoscut”, nu „nu e instalat”;
- marcajul „✓ instalat” și filtrul din interfață.
"""

from __future__ import annotations

from pathlib import Path

from app.installed import (Installed, citeste_deb, citeste_flatpak,
                           citeste_snap, comanda_instalare, detecteaza,
                           nume_pachet)


def alergator_fals(ieșire: str):
    """Întoarce o funcție care „rulează” comanda și întoarce ieșirea fixată."""
    def rulează(args, timeout=5):
        return ieșire
    return rulează


class TestCitireDeb:
    def test_parseaza_pachetele_instalate(self):
        ieșire = ("adduser\t3.137ubuntu1\tinstalled\n"
                  "vlc\t3.0.20-1\tinstalled\n"
                  "vechi\t1.0\tconfig-files\n")
        pachete = citeste_deb(alergator_fals(ieșire))
        assert pachete == {"adduser": "3.137ubuntu1", "vlc": "3.0.20-1"}

    def test_pachetele_stergute_nu_sunt_instalate(self):
        """Starea „config-files” înseamnă „dezinstalat”, nu „instalat”."""
        pachete = citeste_deb(alergator_fals("x\t1.0\tconfig-files\n"),
                              cale_stare=Path("/nu-exista"))
        assert pachete == {}

    def test_iesire_goala_inseamna_nimic_detectat(self):
        assert citeste_deb(alergator_fals(""),
                            cale_stare=Path("/nu-exista")) == {}


class TestCitireSnap:
    def test_parseaza_tabelul(self):
        ieșire = ("Name    Version   Rev    Tracking   Publisher   Notes\n"
                  "code    1.96.4    300    latest    canonical✓  -\n"
                  "firefox 141.0      7000   latest    mozilla✓    -\n")
        snapuri = citeste_snap(alergator_fals(ieșire))
        assert snapuri == {"code": "1.96.4", "firefox": "141.0"}

    def test_antetul_nu_e_pachet(self):
        assert citeste_snap(alergator_fals("Name    Version   Rev\n"),
                            director=Path("/nu-exista")) == {}


class TestCitireFlatpak:
    def test_parseaza_app_id_si_versiune(self):
        ieșire = "org.gimp.GIMP\t2.10.38\norg.kde.krita\t5.2.0\n"
        aplicatii = citeste_flatpak(alergator_fals(ieșire))
        assert aplicatii == {"org.gimp.GIMP": "2.10.38",
                             "org.kde.krita": "5.2.0"}


class TestAsociere:
    def test_nume_pachet_folosește_conventia(self):
        assert nume_pachet({"id": "gimp"}) == "gimp"
        assert nume_pachet({"id": "openshot", "package": "openshot-qt"}) \
            == "openshot-qt"

    def test_asociaza_pachetul_deb(self):
        surse = {"deb": {"gimp": "2.10.38"}, "snap": {}, "flatpak": {}}
        rezultat = detecteaza([{"id": "gimp"}], surse)
        assert rezultat["gimp"] == Installed("gimp", "deb", "gimp", "2.10.38")

    def test_asociaza_snapul_si_flatpakul(self):
        surse = {"deb": {}, "snap": {"firefox": "141.0"},
                 "flatpak": {"org.gimp.GIMP": "2.10.38"}}
        rezultat = detecteaza([
            {"id": "firefox", "snap": "firefox"},
            {"id": "gimp", "flatpak": "org.gimp.GIMP"},
        ], surse)
        assert rezultat["firefox"].source == "snap"
        assert rezultat["gimp"].source == "flatpak"

    def test_nume_de_pachet_sunt_case_insensitive(self):
        surse = {"deb": {"FooBar": "1.0"}, "snap": {}, "flatpak": {}}
        rezultat = detecteaza([{"id": "foobar"}], surse)
        assert rezultat["foobar"].name == "FooBar"

    def test_sursa_indisponibila_nu_inseamna_neinstalat(self):
        """O sursă goală înseamnă „n-am putut verifica”, nu „nu e instalat”."""
        surse = {"deb": {}, "snap": {}, "flatpak": {}}
        assert detecteaza([{"id": "gimp"}], surse) == {}

    def test_deb_are_prioritate_peste_snap(self):
        surse = {"deb": {"vlc": "3.0.20"}, "snap": {"vlc": "3.0.21"},
                 "flatpak": {}}
        rezultat = detecteaza([{"id": "vlc", "snap": "vlc"}], surse)
        assert rezultat["vlc"].source == "deb"



class TestComandaInstalare:
    def test_pachet_ubuntu(self):
        comandă = comanda_instalare({"id": "gimp", "in_ubuntu_repos": True})
        assert comandă == ("sudo apt install gimp", "din pachetele Ubuntu")

    def test_snap_cand_nu_este_in_repo(self):
        comandă = comanda_instalare({"id": "firefox", "snap": "firefox"})
        assert comandă is not None
        assert "snap install firefox" in comandă[0]

    def test_flatpak_cand_nu_exista_alte_surse(self):
        comandă = comanda_instalare({"id": "gimp", "flatpak": "org.gimp.GIMP"})
        assert comandă is not None
        assert "flatpak install flathub org.gimp.GIMP" in comandă[0]

    def test_fara_sursa_nu_inventam_comanda(self):
        assert comanda_instalare({"id": "figma"}) is None


def _app_test() -> dict:
    """O aplicație minimă, pentru card."""
    return {"id": "gimp", "name": "GIMP", "description": "d",
            "license": "foss", "price": "free", "platforms": ["linux"],
            "tags": [], "alternatives": [], "editors_choice": False,
            "popcon_rank": None, "stars": None, "stars_url": "",
            "in_ubuntu_repos": True, "latest_release": "2026-11",
            "confidence": {}}


class TestCatalog:
    def test_coloanele_noi_sunt_in_baza(self, catalog):
        """Numele de pachet sunt în catalog, ca detectarea să le poată folosi."""
        assert catalog.get("gimp")["package"] == "gimp"
        assert catalog.get("openshot")["package"] == "openshot-qt"


class TestInterfata:
    def test_cardul_purta_marcajul_instalat(self, qapp):
        from PySide6.QtWidgets import QLabel

        from app.widgets import AppCard

        card = AppCard(_app_test(), {},
                       installed=Installed("gimp", "deb", "gimp", "2.10.38"))
        texte = [w.text() for w in card.findChildren(QLabel)]
        assert any("instalat" in t for t in texte), texte

    def test_cardul_fara_marcaj_cand_nu_e_instalat(self, qapp):
        from PySide6.QtWidgets import QLabel

        from app.widgets import AppCard

        card = AppCard(_app_test(), {})
        texte = [w.text() for w in card.findChildren(QLabel)]
        assert not any("instalat" in t for t in texte), texte


class TestFiltrare:
    def _ids(self, window) -> list[str]:
        """Cardurile din randarea curenta (nu cele sterse, care asteapta
        `deleteLater` si ar da rezultate vechi)."""
        from app.widgets import AppCard

        ids = []
        for i in range(window.list_box.count()):
            widget = window.list_box.itemAt(i).widget()
            if isinstance(widget, AppCard):
                ids.append(widget.app_id)
        return ids

    def test_filtrul_pastreaza_doar_instalatele(self, catalog, qapp):
        """Filtrul „Doar instalate” ascunde aplicațiile neinstalate."""
        from app.main_window import MainWindow

        window = MainWindow(catalog, detecta=False)
        window.installed = {"gimp": Installed("gimp", "deb", "gimp", "2.10.38")}
        window.state["installed"] = "yes"
        window.refresh_list()
        assert self._ids(window) == ["gimp"]

    def test_filtrul_neinstalate_le_complementa(self, catalog, qapp):
        from app.main_window import MainWindow

        window = MainWindow(catalog, detecta=False)
        window.installed = {"gimp": Installed("gimp", "deb", "gimp", "2.10.38")}
        window.state["installed"] = "no"
        window.refresh_list()
        ids = self._ids(window)
        assert "gimp" not in ids
        assert len(ids) == catalog.app_count - 1


class TestDetectareInThread:
    """Detectarea rulează într-un QThread — și asta a cauzat un segfault.

    Regresie: workerul (`DetectWorker`) nu avea referință Python, deci
    garbage collectorul îl distrugea în timp ce thread-ul lucra, iar Qt
    accesa un obiect C++ deja eliberat → segfault la pornirea aplicației.
    Testele anterioare evitau exact acest drum (`detecta=False`), deci
    bugul trecuse neobservat.
    """

    def test_detectarea_rezultatul_ajunge_in_fereastra(self, catalog, qapp,
                                                       monkeypatch):
        from PySide6.QtCore import QEventLoop, QTimer

        from app import main_window

        monkeypatch.setattr(
            main_window, "detecteaza",
            lambda apps: {"gimp": Installed("gimp", "deb", "gimp", "2.10.38")})
        window = main_window.MainWindow(catalog)   # detectare pornită
        try:
            buclă = QEventLoop()
            QTimer.singleShot(3000, buclă.quit)
            buclă.exec()                            # procesează semnalul
            assert "gimp" in window.installed, "rezultatul nu a ajuns în fereastră"
            assert "instalate" in window.installed_label.text()
        finally:
            window.close()

    def test_workerul_supravietuieste_garbage_collectorului(self, catalog,
                                                             qapp, monkeypatch):
        """Referința Python a workerului trebuie păstrată cât timp rulează."""
        import gc

        from app import main_window

        monkeypatch.setattr(main_window, "detecteaza", lambda apps: {})
        window = main_window.MainWindow(catalog)
        try:
            gc.collect()   # fără referință, workerul ar fi eliberat aici
            assert window._detect_worker is not None, \
                "workerul trebuie păstrat ca referință (vezi net.py)"
            assert window._detect_thread is not None
        finally:
            window.close()

    def test_inchiderea_fereastrei_opreste_threadul(self, catalog, qapp,
                                                      monkeypatch):
        """La închidere, threadul e oprit — altfel ar depăși fereastra."""
        from app import main_window

        monkeypatch.setattr(main_window, "detecteaza", lambda apps: {})
        window = main_window.MainWindow(catalog)
        window.close()
        assert window._detect_thread is None
