#!/usr/bin/env python3
"""Alterna — punctul de intrare al aplicației desktop (PySide6 / Qt Widgets).

Citește catalog.db (generat de tools/build_catalog.py) și reproduce macheta
mockup-ui/ (sec. 13 din IDEI_PROIECT.md).

Utilizare:
    python -m app.main [--db cale/către/catalog.db]
    python -m app.main --selftest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from .db import Catalog, CatalogError
from .main_window import MainWindow
from .paths import default_catalog_path, logos_dir, resource_root
from .theme import apply_theme


def run_selftest(db_path: Path) -> int:
    """Verifică resursele aplicației și afișează un raport pe stdout.

    Folosit pentru QA-ul pachetului AppImage (.deb) și pentru diagnosticarea
    unor instalări raportate ca având probleme.
    """
    print(f"resurse: {resource_root()}")
    print(f"catalog: {db_path} (există: {db_path.exists()})")

    if not db_path.exists():
        print("REZULTAT: EROARE — catalogul lipseste")
        return 1

    try:
        catalog = Catalog(db_path)
    except CatalogError as exc:
        print(f"REZULTAT: EROARE — catalog invalid: {exc}")
        return 1

    try:
        apps = catalog.search()
        categories = len(catalog.categories)
        logo_dir = logos_dir()
        logo_files = list(logo_dir.glob("*")) if logo_dir.is_dir() else []
        with_logo = 0
        for app in apps:
            for ext in ("svg", "png"):
                if (logo_dir / f"{app['id']}.{ext}").exists():
                    with_logo += 1
                    break

        print(f"aplicatii: {len(apps)}")
        print(f"categorii: {categories}")
        print(f"logo-uri: {len(logo_files)} fișiere, {with_logo} aplicații cu logo")
        print(f"generat la: {catalog.generated_at}")
        ok = len(apps) > 0 and categories > 0
        print(f"REZULTAT: {'OK' if ok else 'EROARE'}")
        return 0 if ok else 1
    finally:
        catalog.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Alterna — alternative software, offline")
    parser.add_argument("--db", type=Path,
                        default=default_catalog_path(),
                        help="calea către catalog.db (implicit: catalogul inclus în aplicație)")
    parser.add_argument("--selftest", action="store_true",
                        help="verifică resursele incluse și afișează un raport, apoi iese")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest(args.db)

    app = QApplication(sys.argv)
    app.setApplicationName("Alterna")
    app.setOrganizationName("Alterna")

    try:
        catalog = Catalog(args.db)
    except CatalogError as exc:
        QMessageBox.critical(None, "Alterna — catalog lipsă", str(exc))
        return 1

    from PySide6.QtCore import QSettings
    apply_theme(app, QSettings("Alterna", "Alterna").value("theme", "system"))

    window = MainWindow(catalog)
    window.show()
    code = app.exec()
    catalog.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
