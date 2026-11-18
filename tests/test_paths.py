"""Teste pentru localizarea resurselor (app/paths.py).

Modulul trebuie să funcționeze identic în development și în bundle-ul
PyInstaller, unde resursele stau în ``sys._MEIPASS``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app import paths


ROOT = Path(__file__).resolve().parent.parent


def test_resource_root_in_development_is_project_root():
    assert paths.resource_root() == ROOT


def test_default_catalog_path_points_to_catalog_db():
    """Calea implicită este catalog.db, în directorul resurselor."""
    path = paths.default_catalog_path()
    assert path.name == "catalog.db"
    assert path.parent == paths.resource_root()


def test_directorul_de_date_respecta_xdg(monkeypatch, tmp_path):
    """Directorul de date al utilizatorului respectă XDG_DATA_HOME."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.user_data_dir() == tmp_path / "Alterna"
    assert paths.user_catalog_path() == tmp_path / "Alterna" / "catalog.db"


def test_directorul_de_date_fara_xdg(monkeypatch, tmp_path):
    """Fără XDG_DATA_HOME se folosește ~/.local/share."""
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    assert paths.user_data_dir() == tmp_path / ".local" / "share" / "Alterna"


def test_catalogul_utilizatorului_are_preferenta(monkeypatch, tmp_path):
    """La pornire, aplicația folosește copia din directorul utilizatorului.

    Astfel o instalare de sistem (read-only în /opt) poate fi actualizată
    fără privilegii: actualizarea se aplică în directorul de date.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(paths, "default_catalog_path",
                        lambda: tmp_path / "bundled" / "catalog.db")
    assert paths.resolve_catalog_path() == tmp_path / "bundled" / "catalog.db"

    copie = paths.user_catalog_path()
    copie.parent.mkdir(parents=True, exist_ok=True)
    copie.write_text("x", encoding="utf-8")
    assert paths.resolve_catalog_path() == copie


def test_calea_explicita_are_preferenta(monkeypatch, tmp_path):
    """`--db` explicit câștigă peste tot."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    explicit = tmp_path / "alt.db"
    assert paths.resolve_catalog_path(explicit) == explicit


def test_logos_dir_contains_logos():
    directory = paths.logos_dir()
    assert directory.name == "logos"
    assert directory.is_dir()
    assert any(directory.iterdir())


def test_check_icon_is_resolvable():
    icon = paths.resource_path("app", "assets", "check.svg")
    assert icon.exists()


def test_resource_root_follows_meipass_when_frozen(monkeypatch, tmp_path):
    """În bundle, rădăcina resurselor este sys._MEIPASS, nu rădăcina codului."""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.resource_root() == tmp_path
    assert paths.resource_path("a", "b.txt") == tmp_path / "a" / "b.txt"


def test_selftest_reports_ok_for_real_catalog(capsys, built_db):
    """Selftest-ul trebuie să confirme catalogul real și să returneze 0."""
    from app.main import run_selftest

    code = run_selftest(built_db)
    output = capsys.readouterr().out
    assert code == 0
    assert "REZULTAT: OK" in output
    import re
    assert re.search(r"aplicatii: \d+", output)
    assert "categorii: 13" in output


def test_selftest_fails_for_missing_catalog(tmp_path, capsys):
    from app.main import run_selftest

    code = run_selftest(tmp_path / "nu-exista.db")
    output = capsys.readouterr().out
    assert code == 1
    assert "EROARE" in output

