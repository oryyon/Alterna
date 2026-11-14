"""Teste pentru sursa unică de versiune (app/version.py)."""

from __future__ import annotations

import re

from app import version


def test_version_is_semantic():
    assert re.fullmatch(r"\d+\.\d+\.\d+", version.VERSION)


def test_app_identity():
    assert version.APP_NAME == "Alterna"
    assert version.APP_ID == "org.alterna.app"
    assert version.COPYRIGHT_HOLDER


def test_deb_version_format():
    """Debian cere partea de revizie ca întreg pozitiv."""
    deb = version.deb_version()
    assert deb == f"{version.VERSION}-1"
    assert re.fullmatch(r"\d+\.\d+\.\d+-\d+", deb)
    assert version.deb_version(3).endswith("-3")


def test_get_version_matches_constant():
    assert version.get_version() == version.VERSION


def test_packaging_scripts_use_version_module():
    """Scripturile de build trebuie să citească versiunea din app/version.py."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for script in ("build_deb.sh", "build_appimage.sh"):
        text = (root / "packaging" / script).read_text(encoding="utf-8")
        assert "app.version" in text, f"{script} trebuie să folosească app/version.py"
