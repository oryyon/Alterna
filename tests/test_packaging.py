"""Teste pentru metadata de distribuție (AppImage)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"


def test_desktop_entry_exists_and_has_required_fields():
    text = (PACKAGING / "alterna.desktop").read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    for key in ("Type=Application", "Name=Alterna", "Exec=alterna",
                "Icon=alterna", "Categories=", "StartupNotify=true"):
        assert key in text, f"lipsă {key} în fișierul .desktop"


def test_desktop_entry_has_single_main_category():
    """appimagetool avertizează la mai multe categorii principale."""
    text = (PACKAGING / "alterna.desktop").read_text(encoding="utf-8")
    match = re.search(r"^Categories=(.+)$", text, re.MULTILINE)
    assert match
    categories = match.group(1).split(";")
    categories = [c for c in categories if c]
    assert len(categories) == 1, "o singură categorie principală"


def test_appdata_is_valid_xml_with_required_metadata():
    root = ET.parse(PACKAGING / "org.alterna.app.appdata.xml").getroot()
    assert root.tag == "component"
    assert root.findtext("id") == "org.alterna.app"
    assert root.findtext("name") == "Alterna"
    assert root.findtext("project_license") == "GPL-3.0-or-later"
    assert root.find("developer") is not None
    assert root.findtext("url[@type='homepage']")


def test_appdata_filename_matches_component_id():
    """appstreamcli cere ca numele fișierului să fie <id>.appdata.xml."""
    root = ET.parse(PACKAGING / "org.alterna.app.appdata.xml").getroot()
    component_id = root.findtext("id")
    assert (PACKAGING / f"{component_id}.appdata.xml").exists()


def test_apprun_is_executable_script():
    run = PACKAGING / "AppRun"
    assert run.exists()
    assert run.read_text(encoding="utf-8").startswith("#!/bin/sh")
    assert "usr/lib/alterna/Alterna" in run.read_text(encoding="utf-8")


def test_build_script_verifies_appimagetool_checksum():
    text = (PACKAGING / "build_appimage.sh").read_text(encoding="utf-8")
    assert "sha256sum -c" in text
    assert "APPIMAGETOOL_SHA256=" in text


def test_build_script_does_not_use_collect_all_pyside6():
    """collect-all pentru tot PySide6 umple bundle-ul cu module nefolosite."""
    text = (PACKAGING / "build_appimage.sh").read_text(encoding="utf-8")
    assert "--collect-all PySide6 \\" not in text
    assert "--collect-all PySide6.QtSvg" in text


def test_icon_exists():
    assert (PACKAGING / "alterna.svg").exists()


def test_deb_build_script_exists_and_is_complete():
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    for required in ("dpkg-deb", "fakeroot", "DEBIAN/control",
                     "postinst", "prerm", "/opt/", "usr/share/applications",
                     "usr/share/icons/hicolor", "usr/share/metainfo",
                     "usr/share/doc"):
        assert required in text, f"lipsă {required} în build_deb.sh"


def test_deb_build_script_uses_lintian():
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    assert "lintian" in text


def test_release_workflow_builds_both_packages():
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "build_appimage.sh" in text
    assert "build_deb.sh" in text
    assert "*.deb" in text
    assert "*.AppImage" in text


def test_deb_dependencies_exist_on_target_system():
    """Dependențele declarate trebuie să existe în arhiva Ubuntu 24.04.

    Ubuntu 24.04 a redenumit libglib2.0-0 în libglib2.0-0t64; declararea
    pachetului vechi făcea .deb-ul neinstalabil.
    """
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    depends = re.search(r"^Depends: (.+)$", text, re.MULTILINE)
    assert depends, "controlul trebuie să declare Depends"
    # Niciun pachet inexistent pe Ubuntu 24.04 nu poate fi dependență grea.
    assert "libglib2.0-0 " not in depends.group(1), \
        "libglib2.0-0 nu mai există în Ubuntu 24.04; folosiți libglib2.0-0t64"
    for pkg in re.findall(r"[a-z0-9.+-]+", depends.group(1)):
        if pkg in ("libc6", "libegl1"):
            continue
        assert "(" not in pkg, f"dependență neașteptată: {pkg}"


def test_deb_keeps_libegl_as_hard_dependency():
    """libEGL este singura bibliotecă Qt critică nebundată în PyInstaller."""
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    depends = re.search(r"^Depends: (.+)$", text, re.MULTILINE)
    assert "libegl1" in depends.group(1)


def test_deb_installs_launcher_in_usr_bin():
    """Aplicația stă în /opt, dar trebuie să fie accesibilă din PATH.

    Fără /usr/bin/alterna, comanda „alterna” și desktop entry-ul cu
    Exec=alterna nu funcționează după instalare.
    """
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    assert 'usr/bin' in text, "pachetul trebuie să creeze directorul usr/bin"
    assert '"$DEB_ROOT/usr/bin/$PACKAGE"' in text, \
        "pachetul trebuie să instaleze launcherul în /usr/bin"
    assert 'alterna-launcher' in text, "buildul trebuie să folosească launcherul"


def test_launcher_script_is_valid_and_executable_path():
    launcher = PACKAGING / "alterna-launcher"
    assert launcher.exists()
    text = launcher.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh")
    assert "/opt/alterna" in text, "launcherul trebuie să refere aplicația din /opt"
    assert "exec" in text


def test_desktop_entry_exec_matches_installed_binary():
    """Exec= din desktop entry trebuie să corespundă binarului instalat."""
    desktop = (PACKAGING / "alterna.desktop").read_text(encoding="utf-8")
    assert "Exec=alterna" in desktop
    build = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    assert 'usr/bin/$PACKAGE' in build, \
        "binarul din /usr/bin trebuie să aibă același nume ca Exec= din .desktop"


def test_packaging_scripts_verify_built_version():
    """Scripturile trebuie să compare versiunea împachetată cu cea din sursă.

    Altfel, un build rulat înainte de schimbarea versiunii publică un
    pachet cu metadata inconsistentă.
    """
    for script in ("build_appimage.sh", "build_deb.sh"):
        text = (PACKAGING / script).read_text(encoding="utf-8")
        assert "BUILT_VER" in text, f"{script} trebuie să verifice versiunea"
        assert "--version" in text, f"{script} trebuie să interogheze binarul"
        assert "Buildul este inconsistent" in text, \
            f"{script} trebuie să eșueze la mismatch de versiune"


def test_deb_normalizes_permissions_without_breaking_binary():
    """Normalizarea permisiunilor nu trebuie să scoată bitul de execuție.

    O rundă anterioară a aplicat chmod 644 după marcarea executabilelor,
    ceea ce lăsa binarul principal neexecutabil (Permission denied).
    """
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    assert 'chmod 755 "$DEB_ROOT/opt/$PACKAGE/$PACKAGE"' in text, \
        "binarul principal trebuie forțat executabil după normalizare"
    assert 'chmod 755 "$DEB_ROOT/usr/bin/$PACKAGE"' in text, \
        "launcherul din /usr/bin trebuie forțat executabil"


def test_launcher_resolves_app_relative_to_itself():
    """Launcherul trebuie să funcționeze și în afara /opt.

    Cu o cale strict absolută, testarea dintr-un director extras eșua,
    deși instalarea reală funcționa.
    """
    launcher = PACKAGING / "alterna-launcher"
    text = launcher.read_text(encoding="utf-8")
    assert "readlink -f" in text, "launcherul trebuie să-și rezolve propria poziție"
    assert "SELF_DIR" in text
    assert '"$SELF_DIR/../../opt/alterna"' in text, \
        "trebuie căutată aplicația relativ la launcher"


def test_both_packaging_scripts_write_to_dist():
    """Ambele pachete trebuie scrise în dist/ — sursa de adevăr comună."""
    for script in ("build_appimage.sh", "build_deb.sh"):
        text = (PACKAGING / script).read_text(encoding="utf-8")
        assert '"$ROOT/dist' in text or '"$DIST' in text, \
            f"{script} trebuie să scrie pachetul în dist/"


def test_deb_control_fields_are_valid():
    """Controlul Debian trebuie să conțină câmpurile obligatorii."""
    text = (PACKAGING / "build_deb.sh").read_text(encoding="utf-8")
    for field in ("Package:", "Version:", "Architecture:", "Maintainer:",
                  "Description:", "Depends:", "Homepage:", "Installed-Size:"):
        assert field in text, f"lipsă câmpul {field} în control"





class TestDependente:
    """pyproject.toml, requirements.txt și requirements-lock.txt nu pot să
    se dezincronizeze — o limită superioară lipsă înseamnă o instalare
    nereproducibilă."""

    def _pyproject(self):
        import tomllib
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        with (root / "pyproject.toml").open("rb") as handle:
            return tomllib.load(handle)

    def _requirements(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        text = (root / "requirements.txt").read_text(encoding="utf-8")
        return [line.strip() for line in text.splitlines()
                if line.strip() and not line.startswith("#")]

    def test_pyproject_exista_si_are_versiune_dinamica(self):
        data = self._pyproject()
        assert data["project"]["name"] == "alterna"
        assert "version" in data["project"]["dynamic"], \
            "versiunea trebuie să vină din app/version.py (sursa unică)"

    def test_dependente_au_limita_superioara(self):
        """Fără limită superioară, o versiune majoră nouă poate rupe aplicația."""
        data = self._pyproject()
        for grup in ("dependencies",):
            for req in data["project"][grup]:
                assert "<" in req, f"{req} nu are limită superioară"
        for grup in ("dev", "build", "all"):
            for req in data["project"]["optional-dependencies"][grup]:
                assert "<" in req, f"{req} nu are limită superioară"

    def test_requirements_sincronizat_cu_pyproject(self):
        """requirements.txt trebuie să declare aceleași limite ca pyproject.toml."""
        data = self._pyproject()
        din_pyproject = {r.split(">=")[0].strip().lower(): r
                         for r in data["project"]["dependencies"]}
        for linie in self._requirements():
            nume = linie.split(">=")[0].strip().lower()
            if nume in din_pyproject:
                assert linie.lower() == din_pyproject[nume].lower(), \
                    f"{nume}: requirements.txt={linie} vs pyproject={din_pyproject[nume]}"

    def test_lockfile_Are_versiuni_exacte(self):
        """Lockfile-ul fixează versiuni exacte, nu intervale."""
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        text = (root / "requirements-lock.txt").read_text(encoding="utf-8")
        for linie in text.splitlines():
            linie = linie.strip()
            if not linie or linie.startswith("#"):
                continue
            assert "==" in linie, f"{linie} nu e o versiune exactă"
            assert ">=" not in linie and "<" not in linie, linie

    def test_dependente_critice_sunt_in_lockfile(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        lock = (root / "requirements-lock.txt").read_text(encoding="utf-8").lower()
        for pachet in ("pyside6", "pyyaml", "ruamel.yaml", "pytest", "pyinstaller"):
            assert pachet in lock, pachet

    def test_pyproject_parseaza_ca_toml_valid(self):
        import tomllib
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        with (root / "pyproject.toml").open("rb") as handle:
            tomllib.load(handle)


class TestDocumentatie:
    """Documentația trebuie să spună același lucru ca realitatea.

    Fiecare număr verificat aici a fost cândva greșit în README sau în
    IDEI_PROIECT.md — testul împiedică recurența.
    """

    def _root(self):
        from pathlib import Path

        return Path(__file__).resolve().parent.parent

    def _read(self, nume: str) -> str:
        return (self._root() / nume).read_text(encoding="utf-8")

    def _apps(self):
        from pathlib import Path
        import yaml

        return [yaml.safe_load(p.read_text(encoding="utf-8"))
                for p in sorted((self._root() / "data" / "apps").glob("*.yaml"))]

    def _numar_de_teste(self) -> int:
        """Numărul de teste colectate de pytest (include parametrizările)."""
        import re
        import subprocess
        import sys

        rezultat = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only"],
            cwd=self._root(), capture_output=True, text=True)
        ieșire = rezultat.stdout
        m = re.search(r"(\d+) tests? collected", ieșire)
        if m:
            return int(m.group(1))
        # rezumatul poate fi ascuns de opțiunile de quiet — sumăm pe fișiere
        per_fișier = re.findall(r"^tests/\S+:\s*(\d+)$", ieșire, re.M)
        assert per_fișier, "nu s-a putut număra testele colectate"
        return sum(int(n) for n in per_fișier)

    def _afirmații_curente(self, document: str) -> str:
        """Textul documentului, fără istoricul.

        Istoricul din IDEI_PROIECT.md consemnează corect numărul de teste
        de la momentul respectiv — nu e o afirmație despre starea de acum.
        """
        text = self._read(document)
        if "## 📝 Istoric modificări" in text:
            text = text.split("## 📝 Istoric modificări")[0]
        return text

    def test_numarul_de_teste_din_readme(self):
        """README-ul trebuie să anunțe numărul real de teste."""
        import re

        n = self._numar_de_teste()
        for document in ("README.md", "IDEI_PROIECT.md"):
            # prinde ambele forme: „194 de teste" și „(194 teste)"
            for afirmatie in re.findall(r"(\d+)\s+de teste|\((\d+)\s+teste",
                                       self._afirmații_curente(document)):
                spus = int(afirmatie[0] or afirmatie[1])
                assert spus == n, \
                    f"{document}: spune {spus} teste, realul e {n}"

    def test_numarul_de_logo_uri_din_documente(self):
        import re

        n = sum(1 for app in self._apps() if app.get("logo"))
        for document in ("README.md", "IDEI_PROIECT.md"):
            for afirmatie in re.findall(r"(\d+)\s+de logo-uri reale",
                                       self._afirmații_curente(document)):
                assert int(afirmatie) == n, \
                    f"{document}: spune {afirmatie} logo-uri, realul e {n}"

    def test_numarul_de_aplicatii_si_categorii(self):
        import re

        n_apps = len(self._apps())
        n_categorii = len(re.findall(r"^\s*- slug:",
                                     self._read("data/categories.yaml"), re.M))
        for document in ("README.md", "IDEI_PROIECT.md"):
            text = self._afirmații_curente(document)
            for afirmatie in re.findall(r"\*\*(\d+) aplicații\*\*", text):
                assert int(afirmatie) == n_apps, \
                    f"{document}: spune {afirmatie} aplicații, realul e {n_apps}"
            for afirmatie in re.findall(r"cele (\d+) categorii", text):
                assert int(afirmatie) == n_categorii, \
                    f"{document}: spune {afirmatie} categorii, realul e {n_categorii}"

    def test_data_ultima_actualizare_din_idei(self):
        """Data din antetul IDEI_PROIECT.md trebuie să fie recentă."""
        import re
        from datetime import date

        text = self._read("IDEI_PROIECT.md")
        m = re.search(r"\*\*Ultima actualizare:\*\* (\d{4}-\d{2}-\d{2})", text)
        assert m, "antetul nu mai spune data ultimei actualizări"
        data = date.fromisoformat(m.group(1))
        assert (date.today() - data).days <= 60, \
            f"antetul spune {data} — peste 60 de zile, e neactualizat"

    def test_pasii_urmatori_sunt_actuali(self):
        """Secțiunea „Stare curentă” nu mai poate promite pași deja făcuți."""
        text = self._read("IDEI_PROIECT.md")
        stare = text.split("## 📍 Stare curentă")[1].split("## ✅")[0]
        for facut in ("crearea repo-ului GitHub", "împachetare AppImage"):
            assert facut not in stare, \
                f"„Stare curentă” promite un pas deja făcut: {facut}"
