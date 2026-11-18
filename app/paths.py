"""Localizarea resurselor Alterna în development și în bundle-urile PyInstaller.

Într-un build PyInstaller, resursele read-only sunt disponibile în ``sys._MEIPASS``.
În development, proiectul este rulat din rădăcina repository-ului.

Atenție: resursele incluse în pachet sunt **read-only pentru utilizator**
(un `.deb` e în `/opt/alterna`, un AppImage e extras în `/tmp`). De aceea
catalogul pe care aplicația îl *modifică* (actualizarea din aplicație) trăiește
în directorul de date al utilizatorului — vezi `user_data_dir`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_root() -> Path:
    """Directorul care conține resursele read-only ale aplicației."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Cale către o resursă inclusă în aplicație."""
    return resource_root().joinpath(*parts)


def default_catalog_path() -> Path:
    """Calea implicită a catalogului SQLite (cel inclus în aplicație)."""
    return resource_path("catalog.db")


def user_data_dir() -> Path:
    """Directorul de date al utilizatorului — singurul loc unde scriem.

    Respectă `XDG_DATA_HOME` (standardul pe Linux); implicit
    `~/.local/share/Alterna`.
    """
    baza = os.environ.get("XDG_DATA_HOME", "").strip()
    radacina = Path(baza) if baza else Path.home() / ".local" / "share"
    return radacina / "Alterna"


def user_catalog_path() -> Path:
    """Calea catalogului în directorul utilizatorului (copia actualizabilă)."""
    return user_data_dir() / "catalog.db"


def resolve_catalog_path(explicit: Path | None = None) -> Path:
    """Catalogul pe care îl folosește aplicația.

    Preferă copia din directorul utilizatorului — cea creată de actualizarea
    din aplicație — și cade înapoi pe cel inclus în pachet. Astfel, o
    instalare de sistem (read-only) poate fi actualizată fără privilegii.
    """
    if explicit is not None:
        return Path(explicit)
    if user_catalog_path().exists():
        return user_catalog_path()
    return default_catalog_path()


def logos_dir() -> Path:
    """Directorul logo-urilor aplicațiilor."""
    return resource_path("data", "logos")


def screenshots_dir() -> Path:
    """Directorul capturilor de ecran ale aplicațiilor."""
    return resource_path("data", "screenshots")
