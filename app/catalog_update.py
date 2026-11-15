"""Alterna — sincronizarea catalogului din GitHub (sec. 7).

Catalogul e un produs generat (`data/` → `catalog.db`), publicat ca asset
la fiecare release. „Actualizează catalogul" descarcă versiunea nouă, îi
verifică amprenta SHA-256 și o înlocuiește pe cea locală, cu backup.

Regulile (sec. 7 + principiul offline-first):
- rețeaua e folosită **doar la cerere explicită**;
- catalogul nou e verificat înainte de a fi folosit — o amprentă care nu
  se potrivește e respinsă, fișierul e șters;
- catalogul vechi e păstrat ca backup, pentru revenire;
- schema incompatibilă e respinsă (nu stricăm o instalare mai nouă).
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path

from . import links
from .net import NetworkError, http_download, http_get_json
from tools.build_catalog import SCHEMA_VERSION  # sursa unică a versiunii schemei

#: Numele fișierului de backup.
BACKUP_SUFFIX = ".bak"


class UpdateError(Exception):
    """Actualizarea nu poate fi aplicată — mesajul e pregătit pentru UI."""


def latest_release(timeout: int = 15) -> dict:
    """Informațiile despre ultima versiune publicată.

    Returnează: {tag, version, url, catalog_url, checksum_url, has_catalog}.
    """
    data = http_get_json(links.LATEST_RELEASE_API, timeout=timeout)
    tag = str(data.get("tag_name") or "")
    version = tag.lstrip("v") or "?"
    assets = {}
    for asset in data.get("assets") or []:
        name = asset.get("name")
        if name:
            assets[name] = asset.get("browser_download_url")

    catalog_url = assets.get(links.CATALOG_ASSET)
    checksum_url = assets.get(links.CATALOG_CHECKSUM_ASSET)
    return {
        "tag": tag,
        "version": version,
        "url": data.get("html_url") or links.LATEST_RELEASE_PAGE,
        "catalog_url": catalog_url,
        "checksum_url": checksum_url,
        "has_catalog": bool(catalog_url),
    }


def sha256_file(path: Path) -> str:
    """Amprenta SHA-256 a unui fișier."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum(text: str) -> str:
    """Extrage amprenta dintr-un fișier `.sha256` (format standard)."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # formatul standard: "<amprenta>  <nume_fișier>"
        parts = line.split()
        if parts:
            return parts[0].lower()
    return ""


def verify_checksum(path: Path, expected: str) -> None:
    """Verifică amprenta unui fișier descărcat; altfel îl șterge.

    Un catalog cu amprenta greșită nu e instalat niciodată.
    """
    if not expected:
        path.unlink(missing_ok=True)
        raise UpdateError("Fișierul de amprentă SHA-256 e gol sau ilizibil — "
                          "catalogul a fost respins.")
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        path.unlink(missing_ok=True)
        raise UpdateError(
            f"Amprenta catalogului nu se potrivește (așteptat {expected[:12]}…, "
            f"primit {actual[:12]}…). Fișierul a fost șters; catalogul tău "
            f"rămâne neatins.")


def check_schema(db_path: Path) -> int:
    """Verifică versiunea schemei a unui catalog descărcat."""
    try:
        con = sqlite3.connect(db_path)
        try:
            meta = dict(con.execute("SELECT key, value FROM metadata"))
        finally:
            con.close()
    except sqlite3.Error as exc:
        raise UpdateError(f"Catalogul descărcat nu e o bază de date validă: {exc}") from exc
    try:
        version = int(meta.get("schema_version", 0))
    except ValueError:
        version = 0
    if version > SCHEMA_VERSION:
        raise UpdateError(
            f"Catalogul descărcat e pentru o versiune nouă a aplicației "
            f"(schema {version}, aplicația suportă {SCHEMA_VERSION}). "
            f"Actualizează mai întâi Alterna.")
    return version


def download_catalog(dest_dir: Path, timeout: int = 60) -> Path:
    """Descarcă catalogul + amprenta, verifică amprenta, întoarce calea."""
    release = latest_release(timeout=timeout)
    if not release["catalog_url"]:
        raise UpdateError(
            f"Versiunea {release['tag']} nu publică un catalog "
            f"({links.CATALOG_ASSET}).")
    if not release["checksum_url"]:
        raise UpdateError(
            f"Versiunea {release['tag']} nu publică amprenta SHA-256 — "
            f"fără ea catalogul nu poate fi verificat, deci nu e descărcat.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = dest_dir / links.CATALOG_ASSET
    checksum_path = dest_dir / links.CATALOG_CHECKSUM_ASSET
    try:
        http_download(release["catalog_url"], catalog_path, timeout=timeout)
        http_download(release["checksum_url"], checksum_path, timeout=timeout)
        expected = parse_checksum(checksum_path.read_text(encoding="utf-8"))
        verify_checksum(catalog_path, expected)
        check_schema(catalog_path)
    except NetworkError:
        catalog_path.unlink(missing_ok=True)
        raise
    finally:
        checksum_path.unlink(missing_ok=True)
    return catalog_path


def apply_catalog(new_db: Path, current_db: Path) -> Path:
    """Înlocuiește catalogul local cu cel descărcat, păstrând un backup.

    Returnează calea fișierului de backup.
    """
    if not new_db.exists():
        raise UpdateError("Catalogul descărcat lipsește.")
    backup = current_db.with_suffix(current_db.suffix + BACKUP_SUFFIX)
    if current_db.exists():
        shutil.copy2(current_db, backup)
    try:
        shutil.copy2(new_db, current_db)
    except OSError as exc:
        # catalogul original e salvat în backup; nu l-am stricat
        raise UpdateError(f"Catalogul nou n-a putut fi copiat: {exc}") from exc
    return backup
