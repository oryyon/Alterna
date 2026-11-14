"""Configurare pytest pentru Alterna.

Rulare:  python -m pytest        (din rădăcina proiectului)
Testele GUI folosesc platforma Qt „offscreen" (fără fereastre reale).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def built_db(tmp_path_factory):
    """catalog.db construit din data/ reală, într-un fișier temporar."""
    from tools.build_catalog import build
    out = tmp_path_factory.mktemp("db") / "catalog.db"
    assert build(ROOT / "data", out), "build-ul catalogului a eșuat"
    return out


@pytest.fixture(scope="session")
def catalog(built_db):
    from app.db import Catalog
    cat = Catalog(built_db)
    yield cat
    cat.close()


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(["test"])
    yield app
