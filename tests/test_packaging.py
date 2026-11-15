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



