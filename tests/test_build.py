"""Teste pentru tools/build_catalog.py — validări și schemă (sec. 17)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.build_catalog import build

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _copy_data(tmp_path: Path) -> Path:
    import shutil
    dest = tmp_path / "data"
    shutil.copytree(DATA, dest)
    return dest


class TestBuildReal:
    def test_build_ok(self, built_db):
        assert built_db.exists()

    def test_counts(self, built_db):
        con = sqlite3.connect(built_db)
        apps = con.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        cats = con.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        tax = con.execute("SELECT COUNT(*) FROM taxonomy").fetchone()[0]
        meta = dict(con.execute("SELECT key, value FROM metadata"))
        con.close()
        assert apps == 100 and int(meta["app_count"]) == 100
        assert cats == 13
        assert tax == 18  # taxonomia Securitate (sec. 15)
        assert meta["schema_version"] == "1"

    def test_popularity_column(self, built_db):
        con = sqlite3.connect(built_db)
        rows = con.execute(
            "SELECT COUNT(*) FROM applications WHERE popularity IS NULL").fetchone()
        dup = con.execute(
            "SELECT popularity, COUNT(*) c FROM applications "
            "GROUP BY popularity HAVING c > 1").fetchall()
        con.close()
        assert rows[0] == 0, "toate aplicațiile trebuie să aibă popularity"
        assert not dup, f"popularity duplicate: {dup}"


class TestValidari:
    """Fiecare regulă din data/README.md trebuie să blocheze build-ul."""

    def _fail(self, tmp_path, nume, continut):
        data = _copy_data(tmp_path)
        (data / "apps" / nume).write_text(continut, encoding="utf-8")
        return build(data, tmp_path / "out.db")

    def test_categorie_invalida(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("category: graphics", "category: nu-exista")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_alternativa_inexistenta(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("alternatives: [krita", "alternatives: [fantoma-app, krita")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_id_diferit_de_fisier(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("id: gimp", "id: altceva")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_camp_obligatoriu_lipsa(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("license: foss", "")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_capcana_boolean_yaml(self, tmp_path):
        """telemetry: yes fără ghilimele → boolean True → eroare (regula 4)."""
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
                .replace("telemetry: none", "telemetry: yes")
        assert not self._fail(tmp_path, "gimp.yaml", bad)

    def test_features_fara_taxonomie(self, tmp_path):
        bad = (DATA / "apps" / "gimp.yaml").read_text(encoding="utf-8") \
            + "\nfeatures:\n  offline: free\n"
        assert not self._fail(tmp_path, "gimp.yaml", bad)
