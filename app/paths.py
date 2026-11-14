"""Localizarea resurselor Alterna în development și în bundle-urile PyInstaller.

Într-un build PyInstaller, resursele read-only sunt disponibile în ``sys._MEIPASS``.
În development, proiectul este rulat din rădăcina repository-ului.
"""

from __future__ import annotations

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
    """Calea implicită a catalogului SQLite."""
    return resource_path("catalog.db")


def logos_dir() -> Path:
    """Directorul logo-urilor aplicațiilor."""
    return resource_path("data", "logos")
