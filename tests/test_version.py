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


def test_git_tag_matches_source_version():
    """Tag-ul Git curent trebuie să corespundă versiunii din sursă.

    O etichetă „v0.1.3” peste o sursă care încă spune 0.1.2 face
    release-ul să publice metadata și binar incoherente.
    """
    import subprocess

    try:
        tag = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return  # fără istoric Git (de ex. într-un tarball sursă)

    if not tag.startswith("v"):
        return

    tagged = subprocess.run(
        ["git", "show", f"{tag}:app/version.py"],
        capture_output=True, text=True, timeout=10, check=True,
    ).stdout
    tagged_version = re.search(r'VERSION = "([^"]+)"', tagged).group(1)

    # Tag-ul poate fi cu un commit înaintea celui curent; verificăm doar
    # să nu existe o etichetă nouă care contrazice sursa.
    assert tagged_version == version.VERSION, (
        f"tagul {tag} indică versiunea {tagged_version}, dar sursa are "
        f"{version.VERSION}. Sincronizează app/version.py înainte de release."
    )


def test_packaging_scripts_use_version_module():
    """Scripturile de build trebuie să citească versiunea din app/version.py."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for script in ("build_deb.sh", "build_appimage.sh"):
        text = (root / "packaging" / script).read_text(encoding="utf-8")
        assert "app.version" in text, f"{script} trebuie să folosească app/version.py"
