"""Alterna — stratul de date peste catalog.db.

catalog.db este generat automat de tools/build_catalog.py din fișierele
YAML (data/) — sec. 7 și 17 din IDEI_PROIECT.md. Acest modul doar citește;
baza nu se editează manual și nici din aplicație.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Etichete afișate (oglindă macheta mockup-ui/script.js)
LICENSE_LABELS = {"foss": "Open Source", "freemium": "Freemium", "commercial": "Comercial"}
PLATFORM_LABELS = {"linux": "Linux", "windows": "Windows", "macos": "macOS",
                   "android": "Android", "web": "Web"}
TELEMETRY_LABELS = {
    "none": "✓ Fără telemetrie",
    "optional": "Opțională (se poate dezactiva)",
    "yes": "Da — colectează date",
}
# Valorile matricei de funcționalități (sec. 15): text pentru afișare / export
FEATURE_DISPLAY = {
    "free": "✓ gratuit",
    "paid": "💲 doar în varianta plătită",
    "partial": "⚠ parțial",
    "no": "✗ Nu",
    "unknown": "—",
}
FEATURE_EXPORT = {
    "free": "gratuit",
    "paid": "doar în varianta plătită",
    "partial": "parțial (cu limitări)",
    "no": "Nu",
    "unknown": "—",
}

_APP_COLS = """id, name, description, category, license, price, developer, website,
               logo, editors_choice, popularity, install_size_mb, size_basis,
               first_release_year, telemetry, romanian_language, popcon_rank,
               stars, stars_url, latest_release, in_ubuntu_repos"""


class CatalogError(Exception):
    """catalog.db lipsește sau are un format neașteptat."""


class Catalog:
    """Acces read-only la catalogul local."""

    def __init__(self, db_path: Path | str) -> None:
        db_path = Path(db_path)
        if not db_path.exists():
            raise CatalogError(
                f"Nu am găsit {db_path}.\n"
                f"Generează-l cu: python tools/build_catalog.py")
        self.db_path = db_path
        try:
            self._con = sqlite3.connect(db_path)
            self._con.row_factory = sqlite3.Row
            meta = dict(self._con.execute("SELECT key, value FROM metadata"))
        except sqlite3.Error as exc:
            raise CatalogError(f"catalog.db invalid: {exc}") from exc
        self.generated_at = meta.get("generated_at", "?")
        self.app_count = int(meta.get("app_count", 0))
        self.categories: list[tuple[str, str]] = [
            (r["slug"], r["name"])
            for r in self._con.execute("SELECT slug, name FROM categories ORDER BY position")]
        self._category_names = dict(self.categories)

    def close(self) -> None:
        self._con.close()

    # ------------------------------------------------------------- interogări
    def taxonomy(self, category_slug: str) -> list[tuple[str, str]]:
        """Taxonomia de funcționalități a categoriei (sau [] dacă nu are — sec. 15)."""
        return [(r["key"], r["label"]) for r in self._con.execute(
            "SELECT key, label FROM taxonomy WHERE category = ? ORDER BY position",
            (category_slug,))]

    def _hydrate(self, row: sqlite3.Row) -> dict:
        app = dict(row)
        app_id = app["id"]
        app["category_name"] = self._category_names.get(app["category"], app["category"])
        for field, sql in (
            ("platforms", "SELECT platform FROM platforms WHERE app_id = ?"),
            ("tags", "SELECT tag FROM tags WHERE app_id = ?"),
            ("alternatives", "SELECT alternative_id FROM alternatives WHERE app_id = ?"),
            ("file_formats", "SELECT format FROM file_formats WHERE app_id = ?"),
            ("sources", "SELECT url FROM sources WHERE app_id = ?"),
        ):
            app[field] = [r[0] for r in self._con.execute(sql, (app_id,))]
        # Marcajele de certitudine (sec. 8): {câmp: nivel}
        app["confidence"] = {
            r["field"]: r["level"] for r in self._con.execute(
                "SELECT field, level FROM confidence WHERE app_id = ?", (app_id,))}
        app["features"] = {
            r["feature_key"]: {"value": r["value"], "note": r["note"]}
            for r in self._con.execute(
                "SELECT feature_key, value, note FROM features WHERE app_id = ?", (app_id,))}
        return app

    def get(self, app_id: str) -> dict | None:
        row = self._con.execute(
            f"SELECT {_APP_COLS} FROM applications WHERE id = ?", (app_id,)).fetchone()
        return self._hydrate(row) if row else None

    def search(self, category: str = "", text: str = "", license_: str = "",
               platform: str = "", price: str = "", sort: str = "") -> list[dict]:
        """Căutare + filtre (sec. 6) + sortare (sec. 16) — prin clauze WHERE în SQL."""
        sql = f"SELECT DISTINCT {_APP_COLS} FROM applications a"
        where, params = [], []

        if category:
            where.append("a.category = ?")
            params.append(category)
        if license_:
            where.append("a.license = ?")
            params.append(license_)
        if price:
            where.append("a.price = ?")
            params.append(price)
        if platform:
            where.append("EXISTS (SELECT 1 FROM platforms p "
                         "WHERE p.app_id = a.id AND p.platform = ?)")
            params.append(platform)
        if text:
            like = f"%{text}%"
            where.append("(a.name LIKE ? OR a.description LIKE ? OR EXISTS "
                         "(SELECT 1 FROM tags t WHERE t.app_id = a.id AND t.tag LIKE ?))")
            params += [like, like, like]

        if where:
            sql += " WHERE " + " AND ".join(where)

        # Sortare (sec. 16) — combinabilă liber cu filtrele și căutarea
        # „implicită" = ordinea editorială a catalogului (câmpul popularity din YAML)
        sql += {
            "az": " ORDER BY lower(a.name)",
            "za": " ORDER BY lower(a.name) DESC",
            "recent": " ORDER BY a.latest_release DESC",
            "mic": " ORDER BY a.install_size_mb IS NULL, a.install_size_mb",
        }.get(sort, " ORDER BY a.popularity IS NULL, a.popularity, a.rowid")

        return [self._hydrate(r) for r in self._con.execute(sql, params)]


def format_size(mb: int | None) -> str:
    """Dimensiunea la instalare, ca în machetă (fmtDimMB)."""
    if mb is None:
        return "—"
    if mb == 0:
        return "0 (aplicație web)"
    if mb >= 1000:
        return f"~{mb / 1000:g} GB"
    return f"~{mb} MB"
